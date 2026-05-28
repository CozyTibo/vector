from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.materialize import execute_canon_pass_for_tenant
from vector.domains.cortex.identity.materialize import classify_identity_kind, execute_identity_pass_for_tenant
from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_shared import append_raw
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def test_classify_slack_deleted_as_inactive_human() -> None:
    kind, reason = classify_identity_kind(
        connector="slack",
        handles={"tibo"},
        display_names=set(),
        emails=set(),
        signal_is_bot=False,
        signal_is_inactive=True,
    )
    assert kind == "inactive_human"
    assert reason == "provider_inactive_actor"


def test_classify_active_slack_as_human() -> None:
    kind, _ = classify_identity_kind(
        connector="slack",
        handles={"tibo"},
        display_names={"thibault"},
        emails={"tibo@example.com"},
        signal_is_bot=False,
        signal_is_inactive=False,
    )
    assert kind == "human"


def _seed_tenant_with_slack_and_notion(
    db_session: Session,
    *,
    slack_deleted: bool,
    notion_email: str | None,
) -> uuid.UUID:
    user = User(email=f"inactive-{uuid.uuid4().hex[:8]}@fizzer.com", full_name="Inactive")
    tenant = Tenant(
        company_name="Inactive Co",
        primary_email=user.email,
        email_domain="fizzer.com",
        slug=f"inactive-{uuid.uuid4().hex[:8]}",
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
    now = datetime.now(UTC)
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
        external_id="U-OLD",
        api_endpoint="https://slack.test/users.list",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="slack",
                connection_id=slack_conn.id,
                source_object_type="slack.user",
                source_object_id="U-OLD",
            ),
            "member": {
                "id": "U-OLD",
                "name": "tibo",
                "is_bot": False,
                "deleted": slack_deleted,
                "profile": {"real_name": "Tibo"},
            },
        },
        http_status=200,
        idempotency_key=f"inactive:slack:{slack_deleted}",
    )
    person = {"email": notion_email} if notion_email else {}
    append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tenant.id,
        connection_id=notion_conn.id,
        connector="notion",
        run_id=notion_run.id,
        source_trigger="test",
        resource_type="notion.user",
        external_id="notion-t",
        api_endpoint="https://api.notion.com/v1/users",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="notion",
                connection_id=notion_conn.id,
                source_object_type="notion.user",
                source_object_id="notion-t",
            ),
            "user": {
                "id": "notion-t",
                "name": "Tibo",
                "person": person,
                "type": "person",
            },
        },
        http_status=200,
        idempotency_key=f"inactive:notion:{notion_email or 'none'}",
    )
    db_session.commit()
    return tenant.id


def test_merged_active_notion_and_deleted_slack_stays_human(db_session: Session) -> None:
    tenant_id = _seed_tenant_with_slack_and_notion(
        db_session,
        slack_deleted=True,
        notion_email="tibo@fizzer.com",
    )
    execute_canon_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=100)
    db_session.commit()
    execute_identity_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=100)
    db_session.commit()
    identity = db_session.scalar(
        select(IdentityEntity).where(
            IdentityEntity.tenant_id == tenant_id,
            IdentityEntity.primary_email == "tibo@fizzer.com",
        ),
    )
    assert identity is not None
    assert identity.kind == "human"


def test_slack_deleted_only_identity_is_inactive_human(db_session: Session) -> None:
    tenant_id = _seed_tenant_with_slack_and_notion(
        db_session,
        slack_deleted=True,
        notion_email=None,
    )
    execute_canon_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=100)
    db_session.commit()
    execute_identity_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=100)
    db_session.commit()
    rows = list(
        db_session.scalars(select(IdentityEntity).where(IdentityEntity.tenant_id == tenant_id)).all(),
    )
    inactive = [r for r in rows if r.kind == "inactive_human"]
    assert len(inactive) >= 1
