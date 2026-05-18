"""Phase 08 Step 20 — synthesis artifact query substrate."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
    get_synthesis_artifact_row_v1,
)
from vector.domains.cortex.synthesis.synthesis_artifact_pins import (
    apply_artifact_query_pins_to_row_v1,
    extract_artifact_query_pins_v1,
)
from vector.domains.cortex.synthesis.synthesis_artifact_query import (
    GP08_QUERY01_GATE_ID_V1,
    PHASE08_SYNTHESIS_ARTIFACT_QUERY_RUNTIME_SCHEMA_VERSION,
    SynthesisArtifactQueryError,
    query_synthesis_artifacts_by_lookup_v1,
    query_synthesis_artifacts_by_replay_identity_v1,
    verify_gp08_query01_pin_extraction_static,
    verify_gp08_query01_tenant_scope_static,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-synthesis-runtime-architecture.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_ARTIFACT_QUERY_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp08_query01_tenant_scope_static()["passed"] is True
    assert verify_gp08_query01_tenant_scope_static()["id"] == GP08_QUERY01_GATE_ID_V1
    assert verify_gp08_query01_pin_extraction_static()["passed"] is True


def test_extract_pins_from_scope_summary() -> None:
    lookup, rqid = extract_artifact_query_pins_v1(
        {
            "retrieval_query_replay_identity": "rqid-test",
            "evidence_scope_summary": {"retrieval_lookup_id": "sha256:" + "f" * 64},
        },
    )
    assert rqid == "rqid-test"
    assert lookup == "sha256:" + "f" * 64


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8qry-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Qry")
    tenant = Tenant(
        company_name="P8QRY",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8qry-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_lookup_required(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    db_session.commit()
    with pytest.raises(SynthesisArtifactQueryError, match="retrieval_lookup_id_required"):
        query_synthesis_artifacts_by_lookup_v1(
            db_session,
            tenant_id=tenant_id,
            retrieval_lookup_id="  ",
        )


@pytest.mark.integration
def test_query_by_lookup_and_rqid(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    lookup_id = "sha256:" + "a" * 64
    rqid = "rqid:p08-step20-query"

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
    artifact_id = uuid.UUID(str(out["artifact_id"]))
    stored = get_synthesis_artifact_row_v1(db_session, tenant_id=tenant_id, artifact_id=artifact_id)
    assert stored is not None
    stored.body_json = {**(stored.body_json or {}), "retrieval_lookup_id": lookup_id}
    apply_artifact_query_pins_to_row_v1(stored, body=stored.body_json)
    db_session.commit()
    assert stored.retrieval_lookup_id == lookup_id
    assert stored.retrieval_query_replay_identity == rqid

    by_lookup = query_synthesis_artifacts_by_lookup_v1(
        db_session,
        tenant_id=tenant_id,
        retrieval_lookup_id=lookup_id,
    )
    assert by_lookup["artifact_count"] >= 1
    assert any(a["artifact_id"] == str(artifact_id) for a in by_lookup["artifacts"])

    by_rqid = query_synthesis_artifacts_by_replay_identity_v1(
        db_session,
        tenant_id=tenant_id,
        retrieval_query_replay_identity=rqid,
    )
    assert by_rqid["artifact_count"] >= 1


def test_doctrine_files_present() -> None:
    root = _repo_root()
    assert (root / "DOCS" / "cortex" / "synthesis" / "phase-08-admin-control-plane-spec.md").is_file()
