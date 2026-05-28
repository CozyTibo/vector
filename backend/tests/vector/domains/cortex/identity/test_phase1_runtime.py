from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.materialize import execute_canon_pass_for_tenant
from vector.domains.cortex.identity.materialize import execute_identity_pass_for_tenant
from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_shared import append_raw
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_dirty_queue import IdentityDirtyQueue
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _seed(
    db_session: Session,
    *,
    include_slack_same_email: bool = False,
    include_slack_same_handle_no_email: bool = False,
) -> uuid.UUID:
    user = User(email=f"ident1-{uuid.uuid4().hex[:8]}@example.com", full_name="Identity1")
    tenant = Tenant(
        company_name="Identity1 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"ident1-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="linear",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    slack_conn: TenantConnection | None = None
    if include_slack_same_email or include_slack_same_handle_no_email:
        slack_conn = TenantConnection(
            tenant_id=tenant.id,
            provider="slack",
            status="active",
            connected_by_user_id=user.id,
        )
        db_session.add(slack_conn)
    db_session.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="linear",
        status="COMPLETED",
        source_trigger="test",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        started_at=datetime.now(UTC),
    )
    db_session.add(run)
    slack_run: IngestionRun | None = None
    if slack_conn is not None:
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
        db_session.add(slack_run)
    db_session.flush()
    ctx = IngestionSyncContext.live_incremental()
    append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="linear",
        run_id=run.id,
        source_trigger="test",
        resource_type="linear.user",
        external_id="linear-user-1",
        api_endpoint="https://api.linear.app/graphql",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="linear",
                connection_id=conn.id,
                source_object_type="linear.user",
                source_object_id="linear-user-1",
            ),
            "user": {"id": "linear-user-1", "name": "Tibo", "email": "tibo@example.com"},
        },
        http_status=200,
        idempotency_key="id1:linear:user:1",
    )
    if slack_conn is not None and slack_run is not None:
        profile = {"real_name": "Tibo"}
        if include_slack_same_email:
            profile["email"] = "tibo@example.com"
        append_raw(
            db_session,
            ctx=ctx,
            tenant_id=tenant.id,
            connection_id=slack_conn.id,
            connector="slack",
            run_id=slack_run.id,
            source_trigger="test",
            resource_type="slack.user",
            external_id="U1",
            api_endpoint="https://slack.test/users.list",
            query_params={},
            payload_body={
                **core_envelope_fields(
                    connector="slack",
                    connection_id=slack_conn.id,
                    source_object_type="slack.user",
                    source_object_id="U1",
                ),
                "member": {
                    "id": "U1",
                    "name": "tibo",
                    "is_bot": False,
                    "profile": profile,
                },
            },
            http_status=200,
            idempotency_key="id1:slack:user:1",
        )
    db_session.commit()
    return tenant.id


def test_phase1_identity_seed_from_canon_actors(db_session: Session) -> None:
    tenant_id = _seed(db_session)
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    dirty_count = int(
        db_session.scalar(
            select(func.count())
            .select_from(IdentityDirtyQueue)
            .where(IdentityDirtyQueue.tenant_id == tenant_id, IdentityDirtyQueue.processed_at.is_(None)),
        )
        or 0,
    )
    assert dirty_count >= 1
    out = execute_identity_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    assert out["status"] == "completed"
    assert out["stats"]["seeded"] >= 1
    assert int(db_session.scalar(select(func.count()).select_from(IdentityEntity).where(IdentityEntity.tenant_id == tenant_id)) or 0) >= 1
    assert int(db_session.scalar(select(func.count()).select_from(IdentityAccount).where(IdentityAccount.tenant_id == tenant_id)) or 0) >= 1


def test_phase2_exact_email_links_to_existing_identity(db_session: Session) -> None:
    tenant_id = _seed(db_session, include_slack_same_email=True)
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    out = execute_identity_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    assert out["status"] == "completed"
    identities = int(
        db_session.scalar(select(func.count()).select_from(IdentityEntity).where(IdentityEntity.tenant_id == tenant_id))
        or 0
    )
    accounts = int(
        db_session.scalar(select(func.count()).select_from(IdentityAccount).where(IdentityAccount.tenant_id == tenant_id))
        or 0
    )
    assert accounts >= 2
    assert identities == 1


def test_phase3_handle_match_links_when_email_missing(db_session: Session) -> None:
    tenant_id = _seed(db_session, include_slack_same_handle_no_email=True)
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    out = execute_identity_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    assert out["status"] == "completed"
    identities = int(
        db_session.scalar(select(func.count()).select_from(IdentityEntity).where(IdentityEntity.tenant_id == tenant_id))
        or 0
    )
    accounts = int(
        db_session.scalar(select(func.count()).select_from(IdentityAccount).where(IdentityAccount.tenant_id == tenant_id))
        or 0
    )
    assert accounts >= 2
    assert identities == 1


def test_phase4_cross_tool_name_match_links_notion_and_slack(db_session: Session) -> None:
    user = User(email=f"ident-ns-{uuid.uuid4().hex[:8]}@example.com", full_name="Identity NS")
    tenant = Tenant(
        company_name="Identity NS Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"ident-ns-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    slack_conn = TenantConnection(
        tenant_id=tenant.id,
        provider="slack",
        status="active",
        connected_by_user_id=user.id,
    )
    notion_conn = TenantConnection(
        tenant_id=tenant.id,
        provider="notion",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add_all([slack_conn, notion_conn])
    db_session.flush()
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
    db_session.add_all([slack_run, notion_run])
    db_session.flush()
    ctx = IngestionSyncContext.live_incremental()
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
                "name": "jpeyruchat",
                "is_bot": False,
                "profile": {"real_name": "Julien Peyruchat"},
            },
        },
        http_status=200,
        idempotency_key="idn:slack:user:1",
    )
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
        idempotency_key="idn:notion:user:1",
    )
    db_session.commit()
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant.id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    out = execute_identity_pass_for_tenant(
        db_session,
        tenant_id=tenant.id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    assert out["status"] == "completed"
    identities = int(
        db_session.scalar(select(func.count()).select_from(IdentityEntity).where(IdentityEntity.tenant_id == tenant.id))
        or 0
    )
    accounts = int(
        db_session.scalar(select(func.count()).select_from(IdentityAccount).where(IdentityAccount.tenant_id == tenant.id))
        or 0
    )
    assert accounts >= 2
    assert identities == 1


def test_phase5_resolver_bump_relinks_existing_accounts(db_session: Session) -> None:
    tenant_id = _seed(db_session, include_slack_same_email=True)
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    first = execute_identity_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
        resolver_version=1,
    )
    db_session.commit()
    assert first["status"] == "completed"
    second = execute_identity_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
        resolver_version=2,
        periodic_rescan_limit=100,
    )
    db_session.commit()
    assert second["status"] == "completed"
    active_accounts = int(
        db_session.scalar(
            select(func.count())
            .select_from(IdentityAccount)
            .where(IdentityAccount.tenant_id == tenant_id, IdentityAccount.unlinked_at.is_(None)),
        )
        or 0
    )
    unlinked_accounts = int(
        db_session.scalar(
            select(func.count())
            .select_from(IdentityAccount)
            .where(IdentityAccount.tenant_id == tenant_id, IdentityAccount.unlinked_at.is_not(None)),
        )
        or 0
    )
    max_version = int(
        db_session.scalar(
            select(func.max(IdentityEntity.resolver_version)).where(IdentityEntity.tenant_id == tenant_id),
        )
        or 0
    )
    assert active_accounts >= 2
    assert unlinked_accounts >= 2
    assert max_version == 2

