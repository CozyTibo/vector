"""Regression tests for identity rematch and same-pass dirty-queue processing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.materialize import execute_canon_pass_for_tenant
from vector.domains.cortex.identity.materialize import (
    _latest_actor_payload,
    _seed_identity_for_actor,
    execute_identity_pass_for_tenant,
)
from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_shared import append_raw, utc_now
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_dirty_queue import IdentityDirtyQueue
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _seed_notion_then_slack(db_session: Session) -> uuid.UUID:
    user = User(email=f"rematch-{uuid.uuid4().hex[:8]}@example.com", full_name="Rematch")
    tenant = Tenant(
        company_name="Rematch Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"rematch-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    notion_conn = TenantConnection(
        tenant_id=tenant.id,
        provider="notion",
        status="active",
        connected_by_user_id=user.id,
    )
    slack_conn = TenantConnection(
        tenant_id=tenant.id,
        provider="slack",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add_all([notion_conn, slack_conn])
    db_session.flush()
    notion_run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=notion_conn.id,
        connector="notion",
        status="COMPLETED",
        source_trigger="test",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        started_at=datetime.now(UTC),
    )
    slack_run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=slack_conn.id,
        connector="slack",
        status="COMPLETED",
        source_trigger="test",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        started_at=datetime.now(UTC),
    )
    db_session.add_all([notion_run, slack_run])
    db_session.flush()
    ctx = IngestionSyncContext.live_incremental()
    append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tenant.id,
        connection_id=notion_conn.id,
        connector="notion",
        run_id=notion_run.id,
        source_trigger="test",
        resource_type="notion.user",
        external_id="notion-julien",
        api_endpoint="https://api.notion.com/v1/users",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="notion",
                connection_id=notion_conn.id,
                source_object_type="notion.user",
                source_object_id="notion-julien",
            ),
            "user": {
                "id": "notion-julien",
                "name": "Julien Peyruchat",
                "person": {"email": "julien.peyruchat@example.com"},
                "type": "person",
            },
        },
        http_status=200,
        idempotency_key="rematch:notion:1",
    )
    append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tenant.id,
        connection_id=slack_conn.id,
        connector="slack",
        run_id=slack_run.id,
        source_trigger="test",
        resource_type="slack.user",
        external_id="U-JULIEN",
        api_endpoint="https://slack.test/users.list",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="slack",
                connection_id=slack_conn.id,
                source_object_type="slack.user",
                source_object_id="U-JULIEN",
            ),
            "member": {
                "id": "U-JULIEN",
                "name": "julien.peyruchat",
                "is_bot": False,
                "profile": {"real_name": "Julien Peyruchat"},
            },
        },
        http_status=200,
        idempotency_key="rematch:slack:1",
    )
    db_session.commit()
    return tenant.id


def test_rematch_updates_existing_account_row_without_duplicate(db_session: Session) -> None:
    """Rematch must UPDATE identity_accounts in place (uq on tenant_id+canon_entity_id)."""
    tenant_id = _seed_notion_then_slack(db_session)
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()

    notion_canon_id = db_session.scalar(
        select(CanonEntity.id).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.connector == "notion",
            CanonEntity.entity_type == "actor",
        ),
    )
    slack_canon_id = db_session.scalar(
        select(CanonEntity.id).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.connector == "slack",
            CanonEntity.entity_type == "actor",
        ),
    )
    assert notion_canon_id is not None and slack_canon_id is not None

    notion_row = _latest_actor_payload(
        db_session,
        tenant_id=tenant_id,
        canon_entity_id=notion_canon_id,
    )
    slack_row = _latest_actor_payload(
        db_session,
        tenant_id=tenant_id,
        canon_entity_id=slack_canon_id,
    )
    assert notion_row is not None and slack_row is not None

    notion_out = _seed_identity_for_actor(
        db_session,
        tenant_id=tenant_id,
        canon_entity=notion_row[0],
        source=notion_row[1],
        raw=notion_row[2],
    )
    assert notion_out["outcome"] == "seeded"
    notion_identity_id = uuid.UUID(notion_out["identity_entity_id"])

    slack_entity = notion_row[0]
    stale_identity = IdentityEntity(
        tenant_id=tenant_id,
        kind="human",
        display_name="Slack placeholder",
        primary_email=None,
        resolver_version=1,
        status="active",
        resolved_at=utc_now(),
    )
    db_session.add(stale_identity)
    db_session.flush()
    slack_account = IdentityAccount(
        tenant_id=tenant_id,
        identity_entity_id=stale_identity.id,
        canon_entity_id=slack_canon_id,
        connector=slack_entity.connector,
        connection_id=slack_entity.connection_id,
        link_tier="seed",
        link_rule="seed_actor",
        confidence="low",
        evidence_json={"seed": "actor"},
        linked_at=utc_now(),
    )
    db_session.add(slack_account)
    db_session.commit()
    slack_account_id = slack_account.id
    rows_before = int(
        db_session.scalar(
            select(func.count()).select_from(IdentityAccount).where(IdentityAccount.tenant_id == tenant_id),
        )
        or 0,
    )
    assert rows_before == 2

    slack_out = _seed_identity_for_actor(
        db_session,
        tenant_id=tenant_id,
        canon_entity=slack_row[0],
        source=slack_row[1],
        raw=slack_row[2],
    )
    db_session.commit()

    assert slack_out["outcome"] == "rematched"
    assert uuid.UUID(slack_out["identity_entity_id"]) == notion_identity_id

    rows_after = int(
        db_session.scalar(
            select(func.count()).select_from(IdentityAccount).where(IdentityAccount.tenant_id == tenant_id),
        )
        or 0,
    )
    assert rows_after == rows_before

    slack_account_after = db_session.get(IdentityAccount, slack_account_id)
    assert slack_account_after is not None
    assert slack_account_after.identity_entity_id == notion_identity_id
    assert slack_account_after.link_rule == "handle_to_email_local_part"
    assert slack_account_after.unlinked_at is None


def test_periodic_rescan_processes_enqueued_items_in_same_pass(db_session: Session) -> None:
    """Empty dirty queue + periodic rescan must process newly enqueued actors in the same pass."""
    tenant_id = _seed_notion_then_slack(db_session)
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()

    execute_identity_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()

    db_session.execute(
        IdentityAccount.__table__.update()
        .where(IdentityAccount.tenant_id == tenant_id)
        .values(link_rule="seed_actor", link_tier="seed", confidence="low")
    )
    db_session.execute(
        IdentityEntity.__table__.update()
        .where(IdentityEntity.tenant_id == tenant_id)
        .values(resolver_version=1)
    )
    db_session.execute(
        IdentityDirtyQueue.__table__.delete().where(IdentityDirtyQueue.tenant_id == tenant_id),
    )
    db_session.commit()

    out = execute_identity_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=500,
        periodic_rescan_limit=500,
    )
    db_session.commit()

    stats = out["stats"]
    assert stats["errors"] == 0
    assert int(stats["processed"]) >= 2
    upgraded = int(
        db_session.scalar(
            select(func.count())
            .select_from(IdentityAccount)
            .where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.unlinked_at.is_(None),
                IdentityAccount.link_rule != "seed_actor",
            ),
        )
        or 0,
    )
    assert upgraded >= 1


def test_resolver_bump_enqueued_when_dirty_queue_already_has_pending_rows(db_session: Session) -> None:
    """Pending incremental rows must not block resolver-bump top-up in the same pass."""
    tenant_id = _seed_notion_then_slack(db_session)
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    execute_identity_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
        resolver_version=1,
    )
    db_session.commit()

    actor_ids = list(
        db_session.scalars(
            select(CanonEntity.id).where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.entity_type == "actor",
            ),
        ).all(),
    )
    assert len(actor_ids) >= 2
    db_session.add(
        IdentityDirtyQueue(
            tenant_id=tenant_id,
            canon_entity_id=actor_ids[0],
            reason="actor_updated",
        ),
    )
    db_session.execute(
        IdentityEntity.__table__.update()
        .where(IdentityEntity.tenant_id == tenant_id)
        .values(resolver_version=1),
    )
    db_session.commit()

    out = execute_identity_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=500,
        periodic_rescan_limit=500,
        resolver_version=2,
    )
    db_session.commit()

    assert int(out["stats"]["processed"]) >= 2
    max_version = int(
        db_session.scalar(
            select(func.max(IdentityEntity.resolver_version)).where(IdentityEntity.tenant_id == tenant_id),
        )
        or 0,
    )
    assert max_version >= 2
