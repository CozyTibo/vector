"""Phase 08 Step 14 — SynthesisIntelligenceArtifactV1 materialization."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
    GP08_ART01_GATE_ID_V1,
    SYNTHESIS_ARTIFACT_KINDS_V1,
    SynthesisArtifactMaterializationError,
    build_synthesis_intelligence_artifact_v1,
    compute_synthesis_artifact_digest_v1,
    evaluate_synthesis_publish_barrier_v1,
    get_synthesis_artifact_by_job_id_v1,
    materialize_synthesis_artifact_for_job_v1,
    resolve_synthesis_artifact_kind_v1,
    validate_synthesis_intelligence_artifact_v1,
    verify_gp08_art01_artifact_kind_registry_static,
    verify_gp08_schema01_synthesis_intelligence_artifact_static,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8art-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Art User")
    tenant = Tenant(
        company_name="P8ART",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8art-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
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


def _legal_retrieval_stub() -> dict[str, object]:
    return {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-art",
        "retrieval_evidence_hits": [],
        "retrieval_omission_rows": [],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
    }


@pytest.mark.parametrize(
    "verifier",
    [
        verify_gp08_art01_artifact_kind_registry_static,
        verify_gp08_schema01_synthesis_intelligence_artifact_static,
    ],
)
def test_static_gates(verifier: Callable[[], dict[str, Any]]) -> None:
    out = verifier()
    assert out["passed"] is True


def test_resolve_artifact_kind_from_workload() -> None:
    assert resolve_synthesis_artifact_kind_v1("degradation_brief") == "degradation_brief"
    assert resolve_synthesis_artifact_kind_v1("pipeline_default") in SYNTHESIS_ARTIFACT_KINDS_V1


def test_publish_barrier_deferred_epoch() -> None:
    barrier = evaluate_synthesis_publish_barrier_v1(synthesis_legality_class="synthesis_replay_safe")
    assert barrier["publish_barrier_passed"] is True
    assert barrier["published"] is False
    assert barrier["synthesis_publication_epoch"] is None


def test_artifact_validation_rejects_missing_fields() -> None:
    with pytest.raises(SynthesisArtifactMaterializationError, match="synthesis_intelligence_artifact_invalid"):
        validate_synthesis_intelligence_artifact_v1({"schema_version": 1})


def test_orchestrator_persists_artifact(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["pinned_retrieval_receipt"] = {"retrieval_response": _legal_retrieval_stub()}
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    assert out.get("artifact_id")
    assert out.get("artifact_digest")
    pub = next(row for row in out["execution_trace"] if row["phase"] == "PUBLISH")
    assert pub["status"] == "ok"
    assert pub.get("artifact_id") == out["artifact_id"]
    row = db_session.get(CortexSynthesisArtifact, uuid.UUID(str(out["artifact_id"])))
    assert row is not None
    assert row.published is False
    assert row.synthesis_publication_epoch is None
    assert row.body_json["artifact_digest"] == out["artifact_digest"]
    receipt = out["synthesis_job_receipt"]
    assert receipt.get("artifact_id") == out["artifact_id"]


def test_materialize_idempotent_per_job(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["pinned_retrieval_receipt"] = {"retrieval_response": _legal_retrieval_stub()}
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    job_id = uuid.UUID(out["job_id"])
    job = db_session.get(CortexSynthesisJob, job_id)
    assert job is not None
    first = get_synthesis_artifact_by_job_id_v1(db_session, tenant_id=tenant_id, job_id=job_id)
    assert first is not None
    second = materialize_synthesis_artifact_for_job_v1(
        db_session,
        tenant_id=tenant_id,
        job=job,
        envelope=body,
        synthesis_legality_class=str(out["synthesis_legality_class"]),
        synthesis_job_replay_identity=str(out["synthesis_job_replay_identity"]),
        synthesis_legality_posture=dict(out.get("synthesis_legality_posture") or {}),
        retrieval_ingress=_legal_retrieval_stub(),
        retrieval_subqueries=[],
        claims=list(out.get("claims") or []),
        synthesis_citation_envelope=dict(out.get("synthesis_citation_envelope") or {}),
        synthesis_omission_rows=[],
        synthesis_degradation_rollup=dict(
            (out.get("synthesis_job_receipt") or {}).get("synthesis_degradation_rollup") or {},
        ),
        llm_trace_refs=list(out.get("llm_trace_refs") or []),
        evidence_scope_summary={"hit_count": 0},
    )
    assert second["idempotent_replay"] is True
    assert second["artifact_id"] == str(first.id)


def test_discourse_text_excluded_from_digest() -> None:
    tid = uuid.UUID(int=0)
    jid = uuid.uuid4()
    base = build_synthesis_intelligence_artifact_v1(
        tenant_id=tid,
        job_id=jid,
        envelope={
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
        },
        synthesis_legality_class="synthesis_degraded",
        synthesis_job_replay_identity="sha256:" + "b" * 64,
        synthesis_legality_posture={},
        retrieval_ingress={},
        retrieval_subqueries=[],
        claims=[],
        synthesis_citation_envelope={"citations": [], "citation_count": 0},
        synthesis_omission_rows=[],
        synthesis_degradation_rollup={},
        llm_trace_refs=[],
        evidence_scope_summary={},
    )
    a = dict(base)
    a["claims"] = [{"claim_id": "clm-0001", "discourse_only": True, "text": "one"}]
    a["artifact_digest"] = compute_synthesis_artifact_digest_v1(a)
    b = dict(base)
    b["claims"] = [{"claim_id": "clm-0001", "discourse_only": True, "text": "two"}]
    b["artifact_digest"] = compute_synthesis_artifact_digest_v1(b)
    assert a["artifact_digest"] == b["artifact_digest"]
