"""Phase 4 — canon workers, scheduler, and admin APIs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.admin_entities import list_canon_entities
from vector.settings import get_settings
from vector.domains.cortex.canon.materialize import execute_canon_pass_for_tenant
from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.sync_shared import append_raw
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _seed(db_session: Session) -> uuid.UUID:
    user = User(email=f"canon4-{uuid.uuid4().hex[:8]}@example.com", full_name="Canon4")
    tenant = Tenant(
        company_name="Canon4 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"canon4-{uuid.uuid4().hex[:10]}",
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
        resource_type="linear.issue",
        external_id="issue-abc",
        api_endpoint="https://api.linear.app/graphql",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="linear",
                connection_id=conn.id,
                source_object_type="linear.issue",
                source_object_id="issue-abc",
            ),
            "issue": {
                "id": "issue-abc",
                "identifier": "ENG-1",
                "title": "Ship canon",
                "updatedAt": "2026-03-01T00:00:00Z",
            },
        },
        http_status=200,
        idempotency_key="test:linear:1",
    )
    db_session.commit()
    return tenant.id


def test_plan_passes_skips_canon_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_CANON_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("CORTEX_IDENTITY_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("CORTEX_GRAPH_SCHEDULER_ENABLED", "false")
    from vector.settings import get_settings

    get_settings.cache_clear()
    from vector.domains.cortex.runtime.plan import plan_cortex_passes_v1

    class _Sess:
        def __init__(self) -> None:
            pass

    out = plan_cortex_passes_v1(_Sess(), get_settings())  # type: ignore[arg-type]
    assert out["canon_planned"] == 0
    assert out["identity_planned"] == 0
    assert out["graph_planned"] == 0


def test_list_entities_after_pass(db_session: Session) -> None:
    tenant_id = _seed(db_session)
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    items, total = list_canon_entities(db_session, tenant_id, limit=10)
    assert total >= 1
    assert any(i["entity_type"] == "work_item" for i in items)


def test_admin_canon_endpoints(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    tenant_id = _seed(db_session)
    execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    auth = ("admin", "integration-admin-password")
    readiness = client.get(f"/admin/tenants/{tenant_id}/cortex/canon", auth=auth)
    assert readiness.status_code == 200
    entities = client.get(f"/admin/tenants/{tenant_id}/cortex/canon/entities", auth=auth)
    assert entities.status_code == 200
    assert entities.json()["total_count"] >= 1
    bad = client.post(
        f"/admin/tenants/{tenant_id}/cortex/canon/actions/trigger-pass",
        auth=auth,
        json={"confirmation": "wrong"},
    )
    assert bad.status_code == 400
