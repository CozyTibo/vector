"""Cross-provider linking: GitHub initial login + Slack typo handles."""

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
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _seed_cecile_accounts(db_session: Session) -> uuid.UUID:
    user = User(email=f"cecile-{uuid.uuid4().hex[:8]}@fizzer.com", full_name="Admin")
    tenant = Tenant(
        company_name="Cecile Co",
        primary_email=user.email,
        email_domain="fizzer.com",
        slug=f"cecile-{uuid.uuid4().hex[:8]}",
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
    github_conn = TenantConnection(
        tenant_id=tenant.id,
        provider="github",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add_all([notion_conn, slack_conn, github_conn])
    db_session.flush()
    now = datetime.now(UTC)
    runs = [
        IngestionRun(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            connection_id=conn.id,
            connector=conn.provider,
            status="COMPLETED",
            source_trigger="test",
            sync_mode="incremental",
            replay_mode=False,
            replay_version=1,
            started_at=now,
        )
        for conn in (notion_conn, slack_conn, github_conn)
    ]
    db_session.add_all(runs)
    db_session.flush()
    ctx = IngestionSyncContext.live_incremental()
    run_by_provider = {r.connector: r for r in runs}
    append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tenant.id,
        connection_id=notion_conn.id,
        connector="notion",
        run_id=run_by_provider["notion"].id,
        source_trigger="test",
        resource_type="notion.user",
        external_id="notion-cecile",
        api_endpoint="https://api.notion.com/v1/users",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="notion",
                connection_id=notion_conn.id,
                source_object_type="notion.user",
                source_object_id="notion-cecile",
            ),
            "user": {
                "id": "notion-cecile",
                "name": "Cecile Veneziani",
                "person": {"email": "cecile@fizzer.com"},
                "type": "person",
            },
        },
        http_status=200,
        idempotency_key="cecile:notion",
    )
    append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tenant.id,
        connection_id=slack_conn.id,
        connector="slack",
        run_id=run_by_provider["slack"].id,
        source_trigger="test",
        resource_type="slack.user",
        external_id="U-CECILE",
        api_endpoint="https://slack.test/users.list",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="slack",
                connection_id=slack_conn.id,
                source_object_type="slack.user",
                source_object_id="U-CECILE",
            ),
            "member": {
                "id": "U-CECILE",
                "name": "cecile",
                "is_bot": False,
                "profile": {
                    "real_name": "Cécile Veneziani",
                    "display_name": "ccileveneziani",
                },
            },
        },
        http_status=200,
        idempotency_key="cecile:slack",
    )
    append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tenant.id,
        connection_id=github_conn.id,
        connector="github",
        run_id=run_by_provider["github"].id,
        source_trigger="test",
        resource_type="github.user",
        external_id="50518",
        api_endpoint="https://api.github.com/orgs/fizzer/members",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="github",
                connection_id=github_conn.id,
                source_object_type="github.user",
                source_object_id="50518",
            ),
            "member": {"id": 50518, "login": "cveneziani", "type": "User"},
        },
        http_status=200,
        idempotency_key="cecile:github",
    )
    db_session.commit()
    return tenant.id


def test_cecile_notion_slack_github_merge_to_one_identity(db_session: Session) -> None:
    tenant_id = _seed_cecile_accounts(db_session)
    execute_canon_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=100)
    db_session.commit()
    execute_identity_pass_for_tenant(db_session, tenant_id=tenant_id, source_trigger="test", batch_limit=100)
    db_session.commit()

    identity_count = db_session.scalar(
        select(func.count())
        .select_from(IdentityEntity)
        .where(
            IdentityEntity.tenant_id == tenant_id,
            IdentityEntity.status == "active",
            IdentityEntity.kind == "human",
        ),
    )
    assert identity_count == 1

    accounts = list(
        db_session.scalars(select(IdentityAccount).where(IdentityAccount.tenant_id == tenant_id)).all(),
    )
    assert len(accounts) == 3
    rules = {a.link_rule for a in accounts}
    assert "initial_plus_surname_suffix" in rules
    assert {"exact_normalized_handle", "handle_edit_distance_one"} & rules
