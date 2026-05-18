"""Phase 08 Step 08 — admin synthesis replay explorer HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.normative import PHASE08_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8admrep-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Admin Rep")
    tenant = Tenant(
        company_name="P8ADMREP",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8admrep-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def _minimal_envelope(tenant_id: uuid.UUID) -> dict[str, object]:
    return {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
    }


def test_admin_get_synthesis_replay_explorer_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    execute_synthesis_job_envelope_v1(
        db_session,
        tenant_id=tenant_id,
        body=_minimal_envelope(tenant_id),
    )
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/replay-explorer",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "synthesis_replay_explorer"
    assert body["replay_identity_field"] == PHASE08_REPLAY_IDENTITY_FIELD_V1
    assert len(body["recent_jobs"]) >= 1
    assert body["recent_jobs"][0]["synthesis_job_replay_identity"]


def test_admin_get_synthesis_job_replay_inspector_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    out = execute_synthesis_job_envelope_v1(
        db_session,
        tenant_id=tenant_id,
        body=_minimal_envelope(tenant_id),
    )
    job_id = out["job_id"]
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/jobs/{job_id}/replay-inspector",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "synthesis_replay_inspector"
    assert body["synthesis_job_replay_identity"] == out["synthesis_job_replay_identity"]
    assert body["receipt_digest"] == out["synthesis_job_receipt"]["receipt_digest"]
