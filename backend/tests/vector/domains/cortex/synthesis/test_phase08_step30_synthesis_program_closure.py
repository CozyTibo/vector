"""P08-30 — synthesis program closure + **FF-P08-5**."""

from __future__ import annotations

from vector.domains.cortex.synthesis.normative import PHASE08_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.synthesis.synthesis_program_closure import (
    GP08_P30_PROGRAM_CLOSURE_GATE_ID_V1,
    PHASE08_FREEZE_BUNDLE_FF_P08_5_V1,
    PHASE08_SYNTHESIS_PROGRAM_CLOSURE_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1,
    build_synthesis_program_completion_matrix_v1,
    build_synthesis_program_closure_snapshot_v1,
    verify_gp08_p30_synthesis_program_closure_static,
)


def test_constants() -> None:
    assert PHASE08_SYNTHESIS_PROGRAM_CLOSURE_RUNTIME_SCHEMA_VERSION >= 1
    assert PHASE08_FREEZE_BUNDLE_FF_P08_5_V1 == "FF-P08-5"
    assert len(SYNTHESIS_PROGRAM_COMPLETION_CRITERIA_V1) == 10


def test_completion_matrix_all_core_pass() -> None:
    matrix = build_synthesis_program_completion_matrix_v1(session=None)
    core_ids = {f"C{i:02d}" for i in range(1, 11)}
    core = [r for r in matrix if r.get("criterion_id") in core_ids]
    assert len(core) == 10
    assert all(r["passed"] for r in core)


def test_program_closure_static_gate() -> None:
    out = verify_gp08_p30_synthesis_program_closure_static()
    assert out["id"] == GP08_P30_PROGRAM_CLOSURE_GATE_ID_V1
    assert out["passed"] is True


def test_program_closure_snapshot_shape() -> None:
    snap = build_synthesis_program_closure_snapshot_v1(None, tenant_id="00000000-0000-0000-0000-000000000000")
    assert snap["program_closure_passed"] is True
    assert snap["freeze_bundle_id"] == PHASE08_FREEZE_BUNDLE_FF_P08_5_V1
    assert snap["phase08_program_freeze_version"] == PHASE08_PROGRAM_FREEZE_VERSION
    assert len(snap["completion_criteria"]) >= 10
    assert snap["certification_pack"]["closure_passed"] is True
