"""Phase 08 Step 17 — synthesis replay equivalence proofs (**G-P08-REPLAY-01**)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.normative import PHASE08_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.phase_boundaries import SD_REPLAY_TWIN_V1
from vector.domains.cortex.synthesis.synthesis_bounded_caps import SYNTHESIS_SD_CODES_REGISTRY_V1
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    GP08_REPLAY_01_GATE_ID_V1,
    build_synthesis_replay_equivalence_twin_diff_v1,
    compare_synthesis_structural_artifact_twin_v1,
    synthesis_replay_omissions_from_twin_diff_v1,
)
from vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs import (
    PHASE08_SYNTHESIS_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION,
    load_synthesis_golden_case_v1,
    run_synthesis_golden_replay_equivalence_case_v1,
    run_synthesis_gp08_replay_proof_harness_v1,
    synthesis_inline_twin_required_v1,
    verify_gp08_replay17_golden_double_run_corpus_static,
    verify_gp08_replay17_structural_twin_law_static,
    verify_gp08_replay17_twin_failure_emits_sd_replay_twin_static,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-replay-equivalence-spec.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8rep17-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Rep17")
    tenant = Tenant(
        company_name="P8REP17",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8rep17-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _minimal_envelope(tenant_id: uuid.UUID, *, intent: str = "inspect") -> dict[str, object]:
    return {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": intent,
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
        "selection_policy": {"llm_simulate": "ok"},
    }


def test_proofs_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION >= 1


def test_sd_replay_twin_in_registry() -> None:
    assert SD_REPLAY_TWIN_V1 in SYNTHESIS_SD_CODES_REGISTRY_V1


@pytest.mark.parametrize(
    "verifier",
    [
        verify_gp08_replay17_golden_double_run_corpus_static,
        verify_gp08_replay17_twin_failure_emits_sd_replay_twin_static,
        verify_gp08_replay17_structural_twin_law_static,
    ],
)
def test_gp08_replay17_static_gates(verifier: Callable[[], dict[str, Any]]) -> None:
    out = verifier()
    assert out["passed"] is True
    assert out["id"] == GP08_REPLAY_01_GATE_ID_V1


def test_golden_replay_equivalence_case() -> None:
    case = load_synthesis_golden_case_v1("replay_equivalence/double_run_v1")
    result = run_synthesis_golden_replay_equivalence_case_v1(case)
    assert result["gp08_replay_proof_passed"] is True


def test_harness_passes() -> None:
    out = run_synthesis_gp08_replay_proof_harness_v1()
    assert out["passed"] is True


def test_twin_omissions_on_failure() -> None:
    rows = synthesis_replay_omissions_from_twin_diff_v1(
        {"gp08_replay_proof_passed": False, "structural_twin_passed": False},
    )
    assert rows[0]["sd_code"] == SD_REPLAY_TWIN_V1


def test_structural_twin_detects_claim_kind_drift() -> None:
    art_a = {
        "claims": [{"claim_kind": "observation"}],
        "synthesis_citation_envelope": {"citations": []},
        "synthesis_omission_rows": [],
    }
    art_b = {
        "claims": [{"claim_kind": "hypothesis"}],
        "synthesis_citation_envelope": {"citations": []},
        "synthesis_omission_rows": [],
    }
    diff = compare_synthesis_structural_artifact_twin_v1(art_a, art_b)
    assert diff["structural_twin_passed"] is False


def test_doctrine_present() -> None:
    text = (_repo_root() / "DOCS/cortex/synthesis/phase-08-replay-equivalence-spec.md").read_text(
        encoding="utf-8",
    )
    assert "inline_twin" in text
    assert "prove" in text


def test_inline_twin_required_for_prove_intent() -> None:
    assert synthesis_inline_twin_required_v1({"synthesis_intent": "prove", "synthesis_workload_class": "x"})
    assert synthesis_inline_twin_required_v1(
        {"synthesis_intent": "inspect", "synthesis_workload_class": "replay_equivalence_synthesis"},
    )


@pytest.mark.integration
def test_prove_intent_runs_inline_twin_and_attaches_diff(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    out = execute_synthesis_job_envelope_v1(
        db_session,
        tenant_id=tenant_id,
        body=_minimal_envelope(tenant_id, intent="prove"),
    )
    twin = out.get("replay_equivalence_twin")
    assert isinstance(twin, dict)
    assert twin.get("structural_twin_mode") == "inline_twin"
    assert twin.get("gp08_replay_proof_passed") is True
    assert out.get(PHASE08_REPLAY_IDENTITY_FIELD_V1)


@pytest.mark.integration
def test_replay_equivalence_workload_twin_diff_stable(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id, intent="prove")
    body["synthesis_workload_class"] = "replay_equivalence_synthesis"
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    twin = out["replay_equivalence_twin"]
    assert twin["gp08_replay_proof_passed"] is True
    base = {
        PHASE08_REPLAY_IDENTITY_FIELD_V1: out[PHASE08_REPLAY_IDENTITY_FIELD_V1],
        "synthesis_job_receipt": out["synthesis_job_receipt"],
        "synthesis_intelligence_artifact": out.get("synthesis_intelligence_artifact"),
    }
    diff = build_synthesis_replay_equivalence_twin_diff_v1(base, dict(base))
    assert diff["gp08_replay_proof_passed"] is True
