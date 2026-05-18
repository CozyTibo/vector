"""Phase 08 Step 14 — admin synthesis artifact explorer HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_artifact_materialization import GP08_ART01_GATE_ID_V1
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8artadm-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Art Adm")
    tenant = Tenant(
        company_name="P8ARTADM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8artadm-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_catalog_artifact_explorer_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/artifact-explorer",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["gate_id"] == GP08_ART01_GATE_ID_V1
    assert "degradation_brief" in body["artifact_kinds"]


def test_admin_tenant_artifact_detail_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    body = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
        "pinned_retrieval_receipt": {
            "retrieval_response": {
                "retrieval_legality_class": "retrieval_replay_safe",
                PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:adm-art",
                "retrieval_evidence_hits": [],
                "retrieval_omission_rows": [],
                "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
                "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
            },
        },
    }
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    db_session.commit()
    artifact_id = out["artifact_id"]
    assert artifact_id
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/artifacts/{artifact_id}",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    detail = r.json()
    assert detail["surface_kind"] == "synthesis_artifact_detail"
    assert detail["artifact_id"] == artifact_id
    assert detail["synthesis_intelligence_artifact"]["artifact_kind"] == "degradation_brief"
    assert detail["published"] is False

    r2 = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/artifact-explorer",
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 200
    assert any(row["artifact_id"] == artifact_id for row in r2.json()["recent_artifacts"])
