"""Phase D3 — graph promotion on convergence schedule proof."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_d3_graph_promotion_schedule import (
    PHASE_D3_PROMOTION_SCHEMA_VERSION,
    evaluate_p0_d3_graph_promotion_schedule_proof_v1,
    verify_d3_graph_promotion_schedule_wiring_v1,
)

REPO_ROOT = Path(__file__).resolve().parents[6]


def test_d3_wiring_ok() -> None:
    wiring = verify_d3_graph_promotion_schedule_wiring_v1()
    assert wiring["wiring_ok"] is True
    assert wiring["convergence_promotion_enabled"] is True  # settings flag; worker hook removed (Wave 1)


def test_d3_proof_passes() -> None:
    snapshot = {
        "wiring": {
            "wiring_ok": True,
            "convergence_promotion_enabled": True,
            "phase_d3_schema_version": PHASE_D3_PROMOTION_SCHEMA_VERSION,
            "worker_path": {"m9_promotion_path_ok": True},
        },
        "unpromoted_link_candidates": 100,
        "graph_promoted_edge_count": 50,
        "graph_candidate_count": 200,
        "inline_path": "inline_execution_slice",
        "promoted_on_probe": 5,
        "auth_links_48h_trend": {
            "auth_links_created_recent_48h": 3,
            "auth_links_created_prior_48h": 1,
        },
        "promotion_drain": {"total_promoted": 5},
    }
    proof = evaluate_p0_d3_graph_promotion_schedule_proof_v1(
        closure_git_sha="abc",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
    )
    assert proof["p0_d3_pass"] is True
