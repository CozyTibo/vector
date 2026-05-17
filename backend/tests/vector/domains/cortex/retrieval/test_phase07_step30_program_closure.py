"""P07-30 — program closure + FF-P07-5 + RETRIEVAL-CERT-PACK-1 CI artifact."""

from __future__ import annotations

import uuid

from vector.domains.cortex.retrieval.normative import (
    PHASE07_PROGRAM_FREEZE_VERSION,
    PHASE07_STEP_PROGRAM_COUNT,
)
from vector.domains.cortex.retrieval.retrieval_program_closure import (
    GP07_P30_PROGRAM_CLOSURE_GATE_ID_V1,
    PHASE07_FREEZE_BUNDLE_FF_P07_5_V1,
    PHASE07_RETRIEVAL_PROGRAM_CLOSURE_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1,
    RETRIEVAL_PROGRAM_CLOSURE_SPEC_REF_V1,
    build_retrieval_program_closure_snapshot_v1,
    build_retrieval_program_completion_matrix_v1,
    run_retrieval_gp07_ci_cert_pack_artifact_v1,
    verify_gp07_p30_retrieval_program_closure_static,
)


def test_constants() -> None:
    assert PHASE07_RETRIEVAL_PROGRAM_CLOSURE_RUNTIME_SCHEMA_VERSION >= 1
    assert PHASE07_FREEZE_BUNDLE_FF_P07_5_V1 == "FF-P07-5"
    assert len(RETRIEVAL_PROGRAM_COMPLETION_CRITERIA_V1) == 10
    assert "phase-07-closure-gates-doctrine" in RETRIEVAL_PROGRAM_CLOSURE_SPEC_REF_V1


def test_completion_matrix_all_criteria_present() -> None:
    matrix = build_retrieval_program_completion_matrix_v1(session=None)
    ids = {r.get("criterion_id") for r in matrix if str(r.get("criterion_id", "")).startswith("C")}
    assert ids == {f"C{i:02d}" for i in range(1, 11)}
    assert all(r.get("passed") for r in matrix if str(r.get("criterion_id", "")).startswith("C"))


def test_program_closure_gate_and_ci_artifact() -> None:
    gate = verify_gp07_p30_retrieval_program_closure_static()
    assert gate["id"] == GP07_P30_PROGRAM_CLOSURE_GATE_ID_V1
    assert gate["passed"] is True
    ci = run_retrieval_gp07_ci_cert_pack_artifact_v1()
    assert ci["passed"] is True
    assert ci["pack_bytes"] > 0
    assert ci["verify_passed"] is True


def test_admin_contract_validates_snapshot() -> None:
    from vector.contracts.admin import AdminCortexRetrievalProgramClosureResponse

    tid = uuid.uuid4()
    snap = build_retrieval_program_closure_snapshot_v1(None, tenant_id=tid)
    body = AdminCortexRetrievalProgramClosureResponse.model_validate(snap)
    assert body.tenant_id == str(tid)
    assert body.retrieval_program_freeze_version == PHASE07_PROGRAM_FREEZE_VERSION
    assert body.freeze_bundle_id == PHASE07_FREEZE_BUNDLE_FF_P07_5_V1
    assert len(body.completion_criteria) == 10
    assert PHASE07_STEP_PROGRAM_COUNT == 30
    assert body.program_closure_passed is True
    assert body.certification_pack.get("closure_passed") is True
