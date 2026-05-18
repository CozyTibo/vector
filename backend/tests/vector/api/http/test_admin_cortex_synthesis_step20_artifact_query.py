"""Phase 08 Step 20 — admin synthesis artifact query HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
    get_synthesis_artifact_row_v1,
)
from vector.domains.cortex.synthesis.synthesis_artifact_pins import apply_artifact_query_pins_to_row_v1
from vector.domains.cortex.synthesis.synthesis_artifact_query import GP08_QUERY01_GATE_ID_V1
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8admq20-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Adm Q20")
    tenant = Tenant(
        company_name="P8ADMQ20",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8admq20-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_artifact_query_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/artifact-query",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["gate_id"] == GP08_QUERY01_GATE_ID_V1
    assert "retrieval_lookup_id" in body["supported_filters"]


def test_admin_tenant_artifacts_list_filtered(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    lookup_id = "sha256:" + "c" * 64
    rqid = "rqid:adm-q20-filter"
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
                PHASE07_REPLAY_IDENTITY_FIELD_V1: rqid,
                "retrieval_evidence_hits": [],
                "retrieval_omission_rows": [],
                "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
                "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
            },
        },
    }
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    artifact_id = out["artifact_id"]
    stored = get_synthesis_artifact_row_v1(
        db_session,
        tenant_id=tenant_id,
        artifact_id=uuid.UUID(str(artifact_id)),
    )
    assert stored is not None
    stored.body_json = {**(stored.body_json or {}), "retrieval_lookup_id": lookup_id}
    apply_artifact_query_pins_to_row_v1(stored, body=stored.body_json)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/artifacts",
        params={"retrieval_lookup_id": lookup_id},
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    listed = r.json()
    assert listed["surface_kind"] == "synthesis_artifact_list"
    assert listed["artifact_count"] >= 1
    assert any(row["artifact_id"] == artifact_id for row in listed["artifacts"])
    assert listed["artifacts"][0]["retrieval_lookup_id"] == lookup_id

    r2 = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/artifacts",
        params={"retrieval_query_replay_identity": rqid},
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 200
    assert r2.json()["artifact_count"] >= 1
