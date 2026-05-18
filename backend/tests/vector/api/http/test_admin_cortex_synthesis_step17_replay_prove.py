"""Phase 08 Step 17 — admin synthesis replay prove HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import GP08_REPLAY_01_GATE_ID_V1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8admrep17-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Adm Rep17")
    tenant = Tenant(
        company_name="P8ADMREP17",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8admrep17-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_replay_explorer_includes_harness(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    execute_synthesis_job_envelope_v1(
        db_session,
        tenant_id=tenant_id,
        body={
            "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
            "tenant_id": str(tenant_id),
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
            "retrieval_scope": {},
            "retrieval_pins": {},
        },
    )
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/replay-explorer",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["harness"]["golden_case_id"] == "replay_equivalence/double_run_v1"
    assert body["harness"]["gp08_replay_proof_harness"]["passed"] is True
    assert "structural_twin_passed" in body["twin_diff_fields"]


def test_admin_replay_prove_on_completed_job(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    out = execute_synthesis_job_envelope_v1(
        db_session,
        tenant_id=tenant_id,
        body={
            "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
            "tenant_id": str(tenant_id),
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
            "retrieval_scope": {},
            "retrieval_pins": {},
        },
    )
    job_id = out["job_id"]
    db_session.commit()
    r = client.post(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/jobs/{job_id}/replay-prove",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "synthesis_operator_replay_prove"
    assert body["gate_id"] == GP08_REPLAY_01_GATE_ID_V1
    assert "gp08_replay_proof_passed" in body
    assert body["replay_equivalence_twin"]["structural_twin_mode"] == "operator_twin"
