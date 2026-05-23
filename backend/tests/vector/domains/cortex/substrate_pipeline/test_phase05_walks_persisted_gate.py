"""Unit tests for phase B4 walks persisted gate."""

from __future__ import annotations

from vector.domains.cortex.substrate_pipeline.phase05_walks_persisted_gate import (
    enforce_schedule_pass_walks_persisted_v1,
    resolve_phase05_traversal_outcome_v1,
    summarize_phase05_walk_output_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_BLOCKED,
    PHASE_OUTCOME_COMPLETED,
    PHASE_OUTCOME_SKIPPED_BY_POLICY,
)


def test_summarize_walk_output_merges_supplement() -> None:
    summary = summarize_phase05_walk_output_v1(
        {
            "walks_persisted": 0,
            "walk_schedule_supplement": {
                "walks_persisted": 2,
                "walk_ids": ["a", "b"],
                "primary_octs_walk_id": "a",
            },
        }
    )
    assert summary["walks_persisted"] == 2
    assert summary["walks_available"] == 2


def test_resolve_blocks_when_eligible_and_no_walks() -> None:
    outcome, reason, _raw = resolve_phase05_traversal_outcome_v1(
        {"walks_persisted": 0, "walk_ids": [], "starts_selected": 3},
        {"scheduling_eligible": True},
    )
    assert outcome == PHASE_OUTCOME_BLOCKED
    assert reason == "walks_not_persisted_when_scheduling_eligible"


def test_resolve_completed_when_walks_present() -> None:
    outcome, reason, _raw = resolve_phase05_traversal_outcome_v1(
        {"walks_persisted": 1, "walk_ids": ["w1"]},
        {"scheduling_eligible": True},
    )
    assert outcome == PHASE_OUTCOME_COMPLETED
    assert reason is None


def test_resolve_empty_when_not_eligible() -> None:
    outcome, _reason, _raw = resolve_phase05_traversal_outcome_v1(
        {"walks_persisted": 0, "walk_ids": [], "reason": "no_start_nodes"},
        {"scheduling_eligible": False},
    )
    assert outcome == PHASE_OUTCOME_SKIPPED_BY_POLICY


def test_enforce_schedule_pass_downgrades_empty_eligible() -> None:
    out = enforce_schedule_pass_walks_persisted_v1(
        {
            "scheduled": True,
            "pass": {
                "materialization": {"walks_persisted": 0, "walk_ids": []},
            },
        },
        evaluation={"should_schedule": True},
    )
    assert out["scheduled"] is False
    assert out["reason"] == "walks_not_persisted_when_scheduling_eligible"
