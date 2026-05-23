"""Phase C5 — AA5 jobs_completed proof evaluator."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.synthesis.phase_c5_aa5_synthesis_jobs_completed_gate import (
    PHASE_C5_AA5_GATE_SCHEMA_VERSION,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_c5_aa5_synthesis_jobs_completed import (
    evaluate_p0_c5_aa5_synthesis_jobs_completed_proof_v1,
    verify_c5_aa5_synthesis_jobs_completed_wiring_v1,
)


def test_c5_wiring_ok() -> None:
    repo = Path(__file__).resolve().parents[6]
    wiring = verify_c5_aa5_synthesis_jobs_completed_wiring_v1()
    assert wiring["wiring_ok"] is True
    assert wiring["aa5_strict_enabled"] is True


def test_c5_proof_passes() -> None:
    snapshot = {
        "phase_c5_schema_version": PHASE_C5_AA5_GATE_SCHEMA_VERSION,
        "started_only_aa5_fake_passes": 2,
        "started_only_aa5_pass_lies": 0,
        "wiring": {"wiring_ok": True, "aa5_strict_enabled": True, "strict_aa_panel_schema_version": 3},
    }
    panel = {
        "gates": {
            "AA5": {
                "verdict": "FAIL",
                "criterion": "phase_08 jobs_completed > 0 or lawful documented empty (C5)",
                "evidence": {"fake_started_only_would_pass_legacy": True, "jobs_completed": 0},
            }
        }
    }
    proof = evaluate_p0_c5_aa5_synthesis_jobs_completed_proof_v1(
        closure_git_sha="abc",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        panel=panel,
    )
    assert proof["p0_c5_pass"] is True
