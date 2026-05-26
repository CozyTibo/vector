"""P08-06 — Synthesis job envelope + execution FSM (``synthesis.synthesis_orchestrator``)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.anti_goals import SynthesisAntiGoalViolationError
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
    SynthesisJobContractError,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import (
    PHASE08_SYNTHESIS_JOB_ENVELOPE_RUNTIME_SCHEMA_VERSION,
    SynthesisJobEnvelopeError,
    coerce_body_to_synthesis_job_envelope_v1,
    compute_synthesis_job_envelope_digest_v1,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import (
    GP08_FSM01_GATE_ID_V1,
    PHASE08_SYNTHESIS_ORCHESTRATOR_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_JOB_EXECUTION_PHASES_V1,
    SYNTHESIS_ORCHESTRATOR_BUILD_ID_V1,
    SynthesisOrchestratorError,
    execute_synthesis_job_envelope_v1,
    verify_gp08_fsm01_synthesis_phase_order_static,
    verify_gp08_schema01_synthesis_job_envelope_execution_static,
)
from vector.domains.cortex.synthesis.synthesis_repository import find_idempotent_synthesis_job_v1
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.cortex_synthesis_job_receipt import CortexSynthesisJobReceipt
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8fsm-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 FSM User")
    tenant = Tenant(
        company_name="P8FSM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8fsm-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _legal_retrieval_stub() -> dict[str, object]:
    return {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-fsm",
        "retrieval_evidence_hits": [
            {
                "retrieval_lookup_id": "sha256:" + "e" * 64,
                "source_artifact_kind": "materialization",
                "evidence_legality_class": "replay_safe",
            },
        ],
        "retrieval_omission_rows": [],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
    }


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


def test_phase08_synthesis_orchestrator_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_ORCHESTRATOR_RUNTIME_SCHEMA_VERSION >= 1
    assert PHASE08_SYNTHESIS_JOB_ENVELOPE_RUNTIME_SCHEMA_VERSION >= 1


def test_fsm_phases_match_doctrine_order() -> None:
    assert SYNTHESIS_JOB_EXECUTION_PHASES_V1 == (
        "INGRESS",
        "PLAN",
        "RETRIEVE",
        "BIND",
        "ASSEMBLE",
        "LLM",
        "CLASSIFY",
        "RECEIPT",
        "PUBLISH",
    )


def test_verify_gp08_fsm01_static_passes() -> None:
    out = verify_gp08_fsm01_synthesis_phase_order_static()
    assert out["id"] == GP08_FSM01_GATE_ID_V1
    assert out["passed"] is True


def test_verify_gp08_schema01_job_execution_static_passes() -> None:
    out = verify_gp08_schema01_synthesis_job_envelope_execution_static()
    assert out["passed"] is True


def test_rejects_forbidden_envelope_key() -> None:
    tid = uuid.UUID(int=0)
    with pytest.raises(SynthesisAntiGoalViolationError):
        from vector.domains.cortex.synthesis.synthesis_job_envelope import (
            normalize_synthesis_job_envelope_v1,
        )

        normalize_synthesis_job_envelope_v1(
            {
                **_minimal_envelope(tid),
                "semantic_search": True,
            },
            tenant_id=tid,
        )


def test_rejects_schema_version_mismatch() -> None:
    tid = uuid.UUID(int=0)
    body = _minimal_envelope(tid)
    body["schema_version"] = 2
    with pytest.raises(SynthesisJobContractError, match="schema_version_mismatch"):
        coerce_body_to_synthesis_job_envelope_v1(body, tenant_id=tid)


def test_execute_synthesis_job_fsm_skeleton(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    out = execute_synthesis_job_envelope_v1(
        db_session,
        tenant_id=tenant_id,
        body=_minimal_envelope(tenant_id),
    )
    assert out["status"] == "completed"
    assert out["synthesis_orchestrator_build_id"] == SYNTHESIS_ORCHESTRATOR_BUILD_ID_V1
    trace = out["execution_trace"]
    assert [row["phase"] for row in trace] == list(SYNTHESIS_JOB_EXECUTION_PHASES_V1)
    assert out["synthesis_job_replay_identity"]
    assert out["retrieval_ingress_digest"]
    receipt = out["synthesis_job_receipt"]
    assert receipt["receipt_digest"]
    job = db_session.get(CortexSynthesisJob, uuid.UUID(out["job_id"]))
    assert job is not None
    assert job.status == "completed"
    rows = db_session.query(CortexSynthesisJobReceipt).filter_by(job_id=job.id).all()
    assert len(rows) == 1


def test_execute_with_pinned_retrieval_receipt(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["pinned_retrieval_receipt"] = {"retrieval_response": _legal_retrieval_stub()}
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    retrieve_row = next(row for row in out["execution_trace"] if row["phase"] == "RETRIEVE")
    assert retrieve_row.get("mode") == "pinned_receipt"
    assert out["retrieval_ingress_digest"]


def test_idempotent_replay_returns_existing_job(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["idempotency_key"] = f"idem-{uuid.uuid4().hex[:8]}"
    first = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    second = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    assert second["idempotent_replay"] is True
    assert second["job_id"] == first["job_id"]
    digest = compute_synthesis_job_envelope_digest_v1(
        coerce_body_to_synthesis_job_envelope_v1(body, tenant_id=tenant_id),
    )
    found = find_idempotent_synthesis_job_v1(
        db_session,
        tenant_id=tenant_id,
        idempotency_key=str(body["idempotency_key"]),
        envelope_digest=digest,
    )
    assert found is not None


def test_llm_phase_runs_with_fake_adapter(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["pinned_retrieval_receipt"] = {"retrieval_response": _legal_retrieval_stub()}
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    llm_row = next(row for row in out["execution_trace"] if row["phase"] == "LLM")
    assert llm_row["status"] == "ok"
    assert len(out.get("llm_invocations") or []) >= 1


def test_publish_phase_materializes_artifact(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["pinned_retrieval_receipt"] = {"retrieval_response": _legal_retrieval_stub()}
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    pub = next(row for row in out["execution_trace"] if row["phase"] == "PUBLISH")
    assert pub["status"] == "ok"
    assert out.get("artifact_id")
    assert pub.get("artifact_digest")
