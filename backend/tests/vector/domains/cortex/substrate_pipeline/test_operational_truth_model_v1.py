"""S5.4 — operational truth model tests."""

from __future__ import annotations

from vector.domains.cortex.substrate_pipeline.operational_truth_model_v1 import (
    RULE_M3_AA_NOT_SEMANTIC_GREEN,
    build_operational_truth_cross_check_v1,
)


def test_m3_aa_pass_not_semantic_green_rule_active() -> None:
    cross = build_operational_truth_cross_check_v1(
        continuity_status={"state": "AUTONOMOUS", "execution_lane": "HEALTHY"},
        semantic_readiness={
            "semantic_operator_panel": [{"key": "retrieval_org_link_pct", "severity": "bad"}],
            "graph_truth": {"dup_factor_severity": "ok"},
        },
    )
    assert cross["rule"] == RULE_M3_AA_NOT_SEMANTIC_GREEN
    assert cross["runtime_track_green"] is True
    assert cross["semantic_track_green"] is False
    assert cross["rule_active"] is True
    assert cross["combined_operational_green"] is False


def test_combined_green_when_both_tracks_pass() -> None:
    cross = build_operational_truth_cross_check_v1(
        continuity_status={"state": "AUTONOMOUS", "execution_lane": "HEALTHY"},
        semantic_readiness={
            "semantic_operator_panel": [{"key": "unique_auth_pairs", "severity": "ok"}],
            "graph_truth": {"dup_factor_severity": "ok"},
        },
    )
    assert cross["runtime_track_green"] is True
    assert cross["semantic_track_green"] is True
    assert cross["combined_operational_green"] is True
