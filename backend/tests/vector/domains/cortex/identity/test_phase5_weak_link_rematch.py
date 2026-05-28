"""Weak links must be re-evaluated even when identity.resolver_version is current."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
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


def _seed_maitre_and_notion(db_session: Session) -> uuid.UUID:
    user = User(email=f"weak-{uuid.uuid4().hex[:8]}@fizzer.com", full_name="Weak")
    tenant = Tenant(
        company_name="Weak Co",
        primary_email=user.email,
        email_domain="fizzer.com",
        slug=f"weak-{uuid.uuid4().hex[:8]}",
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
        external_id="notion-j",
        api_endpoint="https://api.notion.com/v1/users",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="notion",
                connection_id=notion_conn.id,
                source_object_type="notion.user",
                source_object_id="notion-j",
            ),
            "user": {
                "id": "notion-j",
                "name": "Julien Peyruchat",
                "person": {"email": "julien@fizzer.com"},
                "type": "person",
            },
        },
        http_status=200,
        idempotency_key="weak:notion",
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
        external_id="U-MAITRE",
        api_endpoint="https://slack.test/users.list",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="slack",
                connection_id=slack_conn.id,
                source_object_type="slack.user",
                source_object_id="U-MAITRE",
            ),
            "member": {
                "id": "U-MAITRE",
                "name": "julien.maitre",
                "is_bot": False,
                "profile": {"real_name": "Julien Maitre"},
            },
        },
        http_status=200,
        idempotency_key="weak:slack",
    )
    db_session.commit()
    return tenant.id


def test_weak_link_reprocessed_and_split_from_peyruchat_identity(db_session: Session) -> None:
    tenant_id = _seed_maitre_and_notion(db_session)
    execute_canon_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=100)
    db_session.commit()
    execute_identity_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=100)
    db_session.commit()

    peyruchat_id = db_session.scalar(
        select(IdentityEntity.id).where(
            IdentityEntity.tenant_id == tenant_id,
            IdentityEntity.primary_email == "julien@fizzer.com",
        ),
    )
    assert peyruchat_id is not None

    accounts = list(
        db_session.scalars(select(IdentityAccount).where(IdentityAccount.tenant_id == tenant_id)).all(),
    )
    for account in accounts:
        if account.identity_entity_id != peyruchat_id:
            account.link_rule = "handle_to_email_local_part"
            account.link_tier = "T3"
            account.confidence = "medium"
    db_session.commit()

    execute_identity_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=100)
    db_session.commit()

    maitre_account = db_session.scalar(
        select(IdentityAccount)
        .join(CanonEntity, CanonEntity.id == IdentityAccount.canon_entity_id)
        .where(
            IdentityAccount.tenant_id == tenant_id,
            CanonEntity.display_label.ilike("%maitre%"),
        ),
    )
    assert maitre_account is not None
    assert maitre_account.identity_entity_id != peyruchat_id
