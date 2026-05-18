"""Phase 08 Step 11 — LLM authority + adapter isolation."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.adapters.llm.fake_llm_adapter import FakeLlmAdapter
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_llm_router import (
    GP08_LLM01_GATE_ID_V1,
    build_synthesis_llm_model_route_catalog_v1,
    compute_prompt_hash_v1,
    execute_synthesis_llm_phase_v1,
    get_model_route_v1,
    should_skip_llm_for_retrieval_legality_v1,
    verify_gp08_llm01_fake_adapter_determinism_static,
    verify_gp08_llm01_model_route_registry_static,
    verify_gp08_llm01_retrieval_legality_gate_static,
    verify_gp08_llm01_sd_mapping_static,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import (
    SynthesisOrchestratorError,
    execute_synthesis_job_envelope_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8llm-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 LLM User")
    tenant = Tenant(
        company_name="P8LLM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8llm-{uuid.uuid4().hex[:8]}",
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


def _legal_retrieval_stub(*, legality: str = "retrieval_replay_safe") -> dict[str, object]:
    return {
        "retrieval_legality_class": legality,
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-llm",
        "retrieval_evidence_hits": [],
        "retrieval_omission_rows": [],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
    }


@pytest.mark.parametrize(
    "verifier",
    [
        verify_gp08_llm01_model_route_registry_static,
        verify_gp08_llm01_fake_adapter_determinism_static,
        verify_gp08_llm01_retrieval_legality_gate_static,
        verify_gp08_llm01_sd_mapping_static,
    ],
)
def test_gp08_llm01_static_gates(verifier: Callable[[], dict[str, Any]]) -> None:
    out = verifier()
    assert out["id"] == GP08_LLM01_GATE_ID_V1
    assert out["passed"] is True


def test_model_route_catalog_lists_struct_v1() -> None:
    cat = build_synthesis_llm_model_route_catalog_v1()
    assert cat["gate_id"] == GP08_LLM01_GATE_ID_V1
    ids = {r["model_route_id"] for r in cat["model_routes"]}
    assert "struct-v1" in ids
    assert "audit-v1" in ids


def test_prompt_hash_stable() -> None:
    route = get_model_route_v1("struct-v1")
    ctx: dict[str, Any] = {"claim_slots": [], "synthesis_omission_sd_codes": []}
    a = compute_prompt_hash_v1(model_route=route, context=ctx)
    b = compute_prompt_hash_v1(model_route=route, context=ctx)
    assert a == b
    assert len(a) == 64


def test_execute_llm_phase_records_invocation() -> None:
    env = {
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
    }
    out = execute_synthesis_llm_phase_v1(
        envelope=env,
        retrieval_ingress=_legal_retrieval_stub(),
        claim_slots=[],
        claims=[],
        synthesis_omission_rows=[],
        synthesis_citation_envelope=None,
    )
    assert out["skipped"] is False
    assert len(out["llm_invocations"]) >= 1
    assert out["llm_invocations"][0]["status"] == "ok"
    assert out["llm_trace_refs"][0]["prompt_hash"]


def test_llm_skipped_on_retrieval_forbidden() -> None:
    skip, reason = should_skip_llm_for_retrieval_legality_v1(
        {"retrieval_legality_class": "retrieval_forbidden"},
        synthesis_intent="inspect",
        execution_partition="authoritative",
    )
    assert skip is True
    assert reason == "retrieval_forbidden"


def test_orchestrator_llm_phase_ok_with_pinned_receipt(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["pinned_retrieval_receipt"] = {"retrieval_response": _legal_retrieval_stub()}
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    llm_row = next(row for row in out["execution_trace"] if row["phase"] == "LLM")
    assert llm_row["status"] == "ok"
    assert len(out["llm_invocations"]) >= 1
    assert out["llm_trace_refs"]


def test_orchestrator_llm_runs_under_exploration_unverifiable(db_session: Session) -> None:
    """Exploration partition allows unverifiable ingress; **SYN-FSM-01** still permits LLM there."""
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["execution_partition"] = "exploration"
    body["pinned_retrieval_receipt"] = {
        "retrieval_response": _legal_retrieval_stub(legality="retrieval_unverifiable"),
    }
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    llm_row = next(row for row in out["execution_trace"] if row["phase"] == "LLM")
    assert llm_row["status"] == "ok"


def test_llm_simulate_schema_fail_closed(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["selection_policy"] = {"llm_simulate": "schema"}
    body["pinned_retrieval_receipt"] = {"retrieval_response": _legal_retrieval_stub()}
    with pytest.raises(SynthesisOrchestratorError, match="synthesis_forbidden"):
        execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    job = db_session.query(CortexSynthesisJob).filter_by(tenant_id=tenant_id).order_by(
        CortexSynthesisJob.created_at.desc(),
    ).first()
    assert job is not None
    llm_row = next(row for row in (job.execution_trace_json or []) if row["phase"] == "LLM")
    assert llm_row.get("llm_schema_failed") is True


def test_fake_adapter_timeout_maps_to_sd() -> None:
    route = get_model_route_v1("struct-v1")
    adapter = FakeLlmAdapter()
    from vector.domains.cortex.synthesis.adapters.llm.protocol import (
        LlmCompletionRequestV1,
        LLM_RESPONSE_FORMAT_JSON_SCHEMA_V1,
    )
    from vector.domains.cortex.synthesis.adapters.llm.protocol import LlmAdapterError

    with pytest.raises(LlmAdapterError, match="llm_timeout"):
        adapter.complete_structured_v1(
            LlmCompletionRequestV1(
                model_route_id="struct-v1",
                provider=str(route["provider"]),
                model=str(route["model"]),
                temperature=0.0,
                max_tokens=100,
                response_format=LLM_RESPONSE_FORMAT_JSON_SCHEMA_V1,
                prompt_hash="sha256:" + "a" * 64,
                context={"claim_slots": []},
                simulate="timeout",
            ),
        )
