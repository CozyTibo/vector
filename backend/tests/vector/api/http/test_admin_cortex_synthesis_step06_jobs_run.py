"""Phase 08 Step 06 — admin synthesis job run + detail HTTP surfaces."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_orchestrator import SYNTHESIS_JOB_EXECUTION_PHASES_V1
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    user = User(email=f"p8adm-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Admin")
    tenant = Tenant(
        company_name="P8ADM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8adm-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_post_synthesis_job_run_returns_execution_trace(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/jobs/run",
        json={
            "schema_version": 1,
            "tenant_id": str(tenant_id),
            "synthesis_workload_class": "pipeline_default",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
        },
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "synthesis_job_run"
    assert body["status"] == "completed"
    assert [row["phase"] for row in body["execution_trace"]] == list(SYNTHESIS_JOB_EXECUTION_PHASES_V1)
    job_id = body["job_id"]

    g = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/jobs/{job_id}",
        auth=("admin", "integration-admin-password"),
    )
    assert g.status_code == 200
    detail = g.json()
    assert detail["job_id"] == job_id
    assert detail["status"] == "completed"
    assert len(detail["execution_trace"]) == 9


def test_admin_post_synthesis_job_run_rejects_forbidden_key(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/jobs/run",
        json={
            "schema_version": 1,
            "tenant_id": str(tenant_id),
            "synthesis_workload_class": "pipeline_default",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
            "rag": True,
        },
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 403
    assert "error" in r.json()
