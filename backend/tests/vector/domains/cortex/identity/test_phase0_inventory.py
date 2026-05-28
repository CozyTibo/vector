from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.materialize import execute_canon_pass_for_tenant
from vector.domains.cortex.identity.inventory import build_actor_signal_inventory
from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_shared import append_raw
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _seed(db_session: Session) -> uuid.UUID:
    user = User(email=f"ident0-{uuid.uuid4().hex[:8]}@example.com", full_name="Identity0")
    tenant = Tenant(
        company_name="Identity0 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"ident0-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    slack = TenantConnection(
        tenant_id=tenant.id,
        provider="slack",
        status="active",
        connected_by_user_id=user.id,
    )
    github = TenantConnection(
        tenant_id=tenant.id,
        provider="github",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add_all([slack, github])
    db_session.flush()
    run_slack = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=slack.id,
        connector="slack",
        status="COMPLETED",
        source_trigger="test",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        started_at=datetime.now(UTC),
    )
    run_gh = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=github.id,
        connector="github",
        status="COMPLETED",
        source_trigger="test",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        started_at=datetime.now(UTC),
    )
    db_session.add_all([run_slack, run_gh])
    db_session.flush()
    ctx = IngestionSyncContext.live_incremental()
    append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tenant.id,
        connection_id=slack.id,
        connector="slack",
        run_id=run_slack.id,
        source_trigger="test",
        resource_type="slack.user",
        external_id="U1",
        api_endpoint="https://slack.test/users.list",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="slack",
                connection_id=slack.id,
                source_object_type="slack.user",
                source_object_id="U1",
            ),
            "member": {
                "id": "U1",
                "name": "tibo",
                "is_bot": False,
                "profile": {"email": "tibo@example.com", "real_name": "Tibo Name"},
            },
        },
        http_status=200,
        idempotency_key="id0:slack:user:u1",
    )
    append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tenant.id,
        connection_id=github.id,
        connector="github",
        run_id=run_gh.id,
        source_trigger="test",
        resource_type="github.user",
        external_id="gh-bot-1",
        api_endpoint="https://api.github.com/orgs/acme/members",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="github",
                connection_id=github.id,
                source_object_type="github.user",
                source_object_id="gh-bot-1",
            ),
            "member": {"id": 5, "login": "dependabot[bot]", "type": "Bot"},
        },
        http_status=200,
        idempotency_key="id0:github:user:bot",
    )
    db_session.commit()
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant.id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    return tenant.id


def test_build_actor_signal_inventory(db_session: Session) -> None:
    tenant_id = _seed(db_session)
    out = build_actor_signal_inventory(db_session, tenant_id=tenant_id, limit=100)
    assert out["sampled_actors"] >= 2
    assert out["email_coverage_pct"] is not None
    assert out["bot_detection_pct"] is not None
    connectors = {c["connector"]: c for c in out["connectors"]}
    assert "slack" in connectors
    assert "github" in connectors
    assert connectors["slack"]["with_email"] >= 1
    assert connectors["github"]["bot_or_service"] >= 1

