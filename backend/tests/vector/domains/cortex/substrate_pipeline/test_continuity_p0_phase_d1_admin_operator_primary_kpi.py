"""Phase D1 — admin operator primary KPI proof evaluator."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_d1_admin_operator_primary_kpi import (
    PHASE_D1_OPERATOR_KPI_SCHEMA_VERSION,
    evaluate_p0_d1_admin_operator_primary_kpi_proof_v1,
    verify_d1_admin_operator_primary_kpi_wiring_v1,
)


def test_d1_wiring_ok() -> None:
    _ = Path(__file__).resolve().parents[6]
    wiring = verify_d1_admin_operator_primary_kpi_wiring_v1()
    assert wiring["wiring_ok"] is True
    assert wiring["drainable_primary_enabled"] is True


def test_d1_proof_passes() -> None:
    drainable = 42
    snapshot = {
        "wiring": {"wiring_ok": True},
        "operator_primary_kpi": {
            "schema_version": PHASE_D1_OPERATOR_KPI_SCHEMA_VERSION,
            "primary_metric_key": "drainable_routable_estimate",
            "primary_metric_value": drainable,
            "drainable_routable_estimate": drainable,
            "raw_minus_mat_banner_deprecated": True,
            "execution_islands": [],
        },
        "overview_operator_primary_kpi": {"primary_metric_key": "drainable_routable_estimate"},
        "canonical_phase_backlog_count": drainable,
        "canonical_signals": ["drainable_routable", "retry_ready"],
    }
    proof = evaluate_p0_d1_admin_operator_primary_kpi_proof_v1(
        closure_git_sha="abc",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
    )
    assert proof["p0_d1_pass"] is True
