"""Unit tests for substrate truth helpers (no DB)."""

from __future__ import annotations

from vector.domains.cortex.substrate_pipeline.substrate_truth_v1 import (
    _compute_overall_status_v1,
    _operator_guidance_v1,
    _queue_ownership_reference_v1,
)


def test_compute_overall_status_stalled() -> None:
    status, rules = _compute_overall_status_v1(
        lease_status="stalled",
        identity_status="healthy",
        isolated_pct=10.0,
        promotion_rule_count=5,
        canonical_lane_status="HEALTHY",
    )
    assert status == "STALLED"
    assert "lease_stalled" in rules


def test_compute_overall_status_degraded_isolation() -> None:
    status, rules = _compute_overall_status_v1(
        lease_status="dirty",
        identity_status="healthy",
        isolated_pct=95.0,
        promotion_rule_count=5,
        canonical_lane_status="HEALTHY",
    )
    assert status == "DEGRADED"
    assert "graph_isolated_pct_above_90" in rules


def test_queue_ownership_reference_has_owners() -> None:
    ref = _queue_ownership_reference_v1()
    assert ref["repair_owner"] == "run_identity_substrate_repair_slice_v1"
    assert "cortex_live" in ref["ingestion_queues"]


def test_operator_guidance_flags_disabled() -> None:
    lines = _operator_guidance_v1(
        overall_status="DEGRADED",
        red_rules=["identity_substrate_degraded"],
        runtime_flags={
            "cortex_post_ingestion_substrate_refresh_enabled": False,
            "cortex_execution_event_triggers_enabled": False,
        },
    )
    assert any("disabled" in line.lower() for line in lines)
