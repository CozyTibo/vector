"""Step 11 alive panel evaluation."""

from __future__ import annotations

from vector.domains.cortex.unlock.step11_alive_panel import (
    TRACK_A_PANEL_HOLD_HOURS_V1,
    build_alive_panel_evaluation_v1,
    evaluate_anti_fake_green_v1,
)


def test_panel_all_green_at_t0() -> None:
    out = build_alive_panel_evaluation_v1(
        org_entities_active=7286,
        authoritative_links_active=200,
        link_candidates=2000,
        lease_last_canonical_outcome="partial_progress",
        released_missing_parent_ref=7715,
        deferrals_before_total=8181,
        deferrals_after_total=466,
        drain_total_succeeded=2,
        completed_walks=16,
        walks_with_authoritative_hop=8,
        entries_materialized=216,
        retrieval_skip_code_counts={},
        raw_minus_mat_admin_gap=8000,
        panel_captured_at="2026-05-22T12:00:00+00:00",
    )
    assert out["step11_pass"] is True
    assert out["track_a_panel_all_green_at_capture"] is True
    assert out["alive_criteria_pass_count"] == 6
    assert out["track_a_panel_hold_hours_required"] == TRACK_A_PANEL_HOLD_HOURS_V1
    assert out["track_a_panel_hold_started_at"] is not None


def test_panel_fails_when_a5_missing() -> None:
    out = build_alive_panel_evaluation_v1(
        org_entities_active=100,
        authoritative_links_active=10,
        link_candidates=100,
        lease_last_canonical_outcome="partial_progress",
        released_missing_parent_ref=1,
        completed_walks=0,
        walks_with_authoritative_hop=0,
        entries_materialized=10,
        retrieval_skip_code_counts={},
        raw_minus_mat_admin_gap=100,
    )
    assert out["step11_pass"] is False
    assert out["criteria"]["A5"]["pass"] is False


def test_anti_fake_passes_when_alive_criteria_green() -> None:
    ok, _ = evaluate_anti_fake_green_v1(raw_minus_mat_admin_gap=9000, alive_criteria_pass_count=6)
    assert ok is True
