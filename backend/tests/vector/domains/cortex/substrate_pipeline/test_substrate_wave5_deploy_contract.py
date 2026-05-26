"""Wave 5 — deploy contract CI gates, baseline diff, soak V6–V8."""

from __future__ import annotations

import pytest

from vector.domains.cortex.execution.scheduling import verify_wave5_deploy_contract_v1
from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
    diff_substrate_truth_against_baseline_v1,
    discover_repo_root_v1,
    evaluate_soak_contract_v6_v8_v1,
    run_substrate_ci_gate_report_v1,
    verify_substrate_coherence_ci_gates_v1,
    verify_wave5_deploy_contract_wiring_v1,
)


def test_verify_substrate_coherence_ci_gates_v1() -> None:
    assert verify_substrate_coherence_ci_gates_v1() == []


@pytest.mark.skipif(discover_repo_root_v1() is None, reason="monorepo root not available in backend-only context")
def test_verify_wave5_deploy_contract_wiring_v1() -> None:
    root = discover_repo_root_v1()
    assert root is not None
    assert verify_wave5_deploy_contract_wiring_v1(repo_root=root) == []


@pytest.mark.skipif(discover_repo_root_v1() is None, reason="monorepo root not available in backend-only context")
def test_verify_wave5_deploy_contract_v1() -> None:
    root = discover_repo_root_v1()
    assert root is not None
    assert verify_wave5_deploy_contract_v1(repo_root=root) == []


def test_run_substrate_ci_gate_report_v1() -> None:
    report = run_substrate_ci_gate_report_v1()
    assert report["passed"] is True
    if discover_repo_root_v1() is None:
        assert report.get("wiring_checks_skipped") is True


def test_baseline_diff_skips_when_baseline_empty() -> None:
    out = diff_substrate_truth_against_baseline_v1(
        {"overall_status": "DEGRADED", "graph": {"promotion_rule_count": 3, "isolated_pct": 50}},
        {"substrate_truth": None},
    )
    assert out["skipped"] is True
    assert out["passed"] is True


def test_baseline_diff_fails_on_promotion_regression() -> None:
    current = {
        "overall_status": "DEGRADED",
        "graph": {"promotion_rule_count": 1, "isolated_pct": 40.0},
    }
    baseline = {
        "acceptance_hints": {"promotion_rule_count_min": 3, "isolated_pct_max": 90.0},
        "substrate_truth": {
            "graph": {"promotion_rule_count": 4, "isolated_pct": 35.0},
        },
    }
    out = diff_substrate_truth_against_baseline_v1(current, baseline)
    assert out["passed"] is False
    assert any("promotion_rule_count" in e for e in out["errors"])


def test_soak_v6_v8_passes_healthy_truth() -> None:
    truth = {
        "graph": {
            "promotion_rule_count": 4,
            "isolated_pct": 55.0,
            "unique_auth_pairs": 100,
        },
        "motion": {"last_graph_projection_hash": "hash-new"},
    }
    soak = evaluate_soak_contract_v6_v8_v1(
        truth,
        prior_graph_hash="hash-old",
    )
    assert soak["passed"] is True
    assert all(c["passed"] for c in soak["checks"])


def test_soak_v8_waiver() -> None:
    truth = {"graph": {"promotion_rule_count": 3, "isolated_pct": 95.0, "unique_auth_pairs": 1}}
    soak = evaluate_soak_contract_v6_v8_v1(truth, isolation_waiver=True)
    v8 = next(c for c in soak["checks"] if c["id"] == "V8")
    assert v8["passed"] is True
