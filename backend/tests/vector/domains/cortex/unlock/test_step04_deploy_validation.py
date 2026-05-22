"""Step 4 A4 validation helpers."""

from __future__ import annotations

from vector.domains.cortex.unlock.step04_deploy_validation import evaluate_a4_canonical_motion_v1


def test_a4_passes_on_total_succeeded() -> None:
    ok, detail = evaluate_a4_canonical_motion_v1(
        drain_summary={"total_succeeded": 12, "canonical_outcome": "topology_wait"},
        lease_last_canonical_outcome="topology_wait",
    )
    assert ok is True
    assert "total_succeeded=12" in detail


def test_a4_passes_on_partial_progress_outcome() -> None:
    ok, _ = evaluate_a4_canonical_motion_v1(
        drain_summary={"total_succeeded": 0, "canonical_outcome": "partial_progress"},
        lease_last_canonical_outcome=None,
    )
    assert ok is True


def test_a4_fails_when_no_motion() -> None:
    ok, detail = evaluate_a4_canonical_motion_v1(
        drain_summary={"total_succeeded": 0, "canonical_outcome": "topology_wait"},
        lease_last_canonical_outcome="topology_wait",
    )
    assert ok is False
    assert "no_motion" in detail


def test_a4_passes_on_deferral_drop() -> None:
    ok, detail = evaluate_a4_canonical_motion_v1(
        drain_summary={"total_succeeded": 0},
        lease_last_canonical_outcome="topology_wait",
        deferrals_before_total=8181,
        deferrals_after_total=466,
    )
    assert ok is True
    assert "deferrals_dropped" in detail
