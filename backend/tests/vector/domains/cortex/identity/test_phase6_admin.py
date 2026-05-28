from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.materialize import execute_canon_pass_for_tenant
from vector.domains.cortex.identity.materialize import execute_identity_pass_for_tenant
from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_shared import append_raw
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _seed(db_session: Session) -> uuid.UUID:
    user = User(email=f"ident6-{uuid.uuid4().hex[:8]}@example.com", full_name="Identity6")
    tenant = Tenant(
        company_name="Identity6 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"ident6-{uuid.uuid4().hex[:8]}",
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
        idempotency_key="id6:linear:user:1",
    )
    db_session.commit()
    execute_canon_pass_for_tenant(db_session, tenant_id=tenant.id, source_trigger="test", batch_limit=100)
    execute_identity_pass_for_tenant(db_session, tenant_id=tenant.id, source_trigger="test", batch_limit=100)
    db_session.commit()
    return tenant.id


def test_identity_admin_endpoints(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    tenant_id = _seed(db_session)
    auth = ("admin", "integration-admin-password")
    readiness = client.get(f"/admin/tenants/{tenant_id}/cortex/identities/readiness", auth=auth)
    assert readiness.status_code == 200
    identities = client.get(f"/admin/tenants/{tenant_id}/cortex/identities", auth=auth)
    assert identities.status_code == 200
    assert identities.json()["total_count"] >= 1
    unresolved = client.get(f"/admin/tenants/{tenant_id}/cortex/identities/unresolved-actors", auth=auth)
    assert unresolved.status_code == 200
    runs = client.get(f"/admin/tenants/{tenant_id}/cortex/identities/runs", auth=auth)
    assert runs.status_code == 200
    bad = client.post(
        f"/admin/tenants/{tenant_id}/cortex/identities/actions/trigger-pass",
        auth=auth,
        json={"confirmation": "wrong"},
    )
    assert bad.status_code == 400

