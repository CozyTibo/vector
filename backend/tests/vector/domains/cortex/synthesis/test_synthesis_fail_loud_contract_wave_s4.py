"""Wave S4 step 16 — synthesis fail-loud contract."""

from __future__ import annotations

from vector.domains.cortex.synthesis.synthesis_fail_loud_contract_v1 import (
    SYNTHESIS_FAIL_LOUD_GATE_IDS_V1,
    verify_synthesis_fail_loud_pipeline_wiring_v1,
)


def test_fail_loud_gate_ids_include_core_gates() -> None:
    assert "phase08_empty_scope_truth" in SYNTHESIS_FAIL_LOUD_GATE_IDS_V1
    assert "synthesis_empty_claims_publish" in SYNTHESIS_FAIL_LOUD_GATE_IDS_V1


def test_phase08_runner_wires_fail_loud_gates() -> None:
    wiring = verify_synthesis_fail_loud_pipeline_wiring_v1()
    assert wiring["wiring_ok"] is True
    assert wiring["errors"] == []
