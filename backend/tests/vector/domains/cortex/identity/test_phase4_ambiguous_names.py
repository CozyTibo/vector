"""Prevent merging distinct people who share a short first-name handle."""

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
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _seed_three_juliens(db_session: Session) -> uuid.UUID:
    user = User(email=f"julien-test-{uuid.uuid4().hex[:8]}@fizzer.com", full_name="Julien test")
    tenant = Tenant(
        company_name="Julien Test Co",
        primary_email=user.email,
        email_domain="fizzer.com",
        slug=f"julien-test-{uuid.uuid4().hex[:8]}",
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
    now = datetime.now(UTC)
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
        started_at=now,
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
        started_at=now,
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
        external_id="notion-jp",
        api_endpoint="https://api.notion.com/v1/users",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="notion",
                connection_id=notion_conn.id,
                source_object_type="notion.user",
                source_object_id="notion-jp",
            ),
            "user": {
                "id": "notion-jp",
                "name": "Julien Peyruchat",
                "person": {"email": "julien@fizzer.com"},
                "type": "person",
            },
        },
        http_status=200,
        idempotency_key="julien:notion:peyruchat",
    )

    for ext_id, slack_name, real_name in (
        ("U-MAITRE", "julien.maitre", "Julien Maitre"),
        ("U-DURIEUX", "julien.durieux", "Julien Durieux"),
        ("U-PEYRUCHAT", "julien", "Julien Peyruchat"),
    ):
        append_raw(
            db_session,
            ctx=ctx,
            tenant_id=tenant.id,
            connection_id=slack_conn.id,
            connector="slack",
            run_id=slack_run.id,
            source_trigger="test",
            resource_type="slack.user",
            external_id=ext_id,
            api_endpoint="https://slack.test/users.list",
            query_params={},
            payload_body={
                **core_envelope_fields(
                    connector="slack",
                    connection_id=slack_conn.id,
                    source_object_type="slack.user",
                    source_object_id=ext_id,
                ),
                "member": {
                    "id": ext_id,
                    "name": slack_name,
                    "is_bot": False,
                    "profile": {"real_name": real_name},
                },
            },
            http_status=200,
            idempotency_key=f"julien:slack:{ext_id}",
        )
    db_session.commit()
    return tenant.id


def test_distinct_juliens_do_not_share_one_identity(db_session: Session) -> None:
    tenant_id = _seed_three_juliens(db_session)
    execute_canon_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=100)
    db_session.commit()
    execute_identity_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=100)
    db_session.commit()

    identity_count = int(
        db_session.scalar(
            select(func.count()).select_from(IdentityEntity).where(IdentityEntity.tenant_id == tenant_id),
        )
        or 0,
    )
    assert identity_count >= 3

    peyruchat_identity_id = db_session.scalar(
        select(IdentityEntity.id).where(
            IdentityEntity.tenant_id == tenant_id,
            IdentityEntity.primary_email == "julien@fizzer.com",
        ),
    )
    assert peyruchat_identity_id is not None

    accounts = list(
        db_session.scalars(
            select(IdentityAccount).where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.unlinked_at.is_(None),
            ),
        ).all(),
    )
    for account in accounts:
        canon = db_session.get(CanonEntity, account.canon_entity_id)
        label = (canon.display_label if canon else "").lower()
        if "maitre" in label or "durieux" in label:
            assert account.identity_entity_id != peyruchat_identity_id
