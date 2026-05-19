"""Unit tests for forward-progress canonical drain semantics."""

from __future__ import annotations

from vector.domains.cortex.canonical.forward_progress.drain_runtime import _classify_drain_outcome
from vector.domains.cortex.canonical.forward_progress.constants import (
    CANONICAL_OUTCOME_FAILED,
    CANONICAL_OUTCOME_IDLE,
    CANONICAL_OUTCOME_PARTIAL_PROGRESS,
    CANONICAL_OUTCOME_PROGRESSED,
    CANONICAL_OUTCOME_TOPOLOGY_WAIT,
)
from vector.domains.cortex.canonical.forward_progress.pass_registry import all_canonical_passes


def test_classify_topology_wait_on_spin() -> None:
    assert (
        _classify_drain_outcome(
            total_succeeded=0,
            total_failed_rows=0,
            topology_wait=True,
            candidate_more_remain=True,
            untreated_estimate=1000,
            hit_slice_cap=False,
        )
        == CANONICAL_OUTCOME_TOPOLOGY_WAIT
    )


def test_classify_partial_progress() -> None:
    assert (
        _classify_drain_outcome(
            total_succeeded=50,
            total_failed_rows=0,
            topology_wait=False,
            candidate_more_remain=True,
            untreated_estimate=500,
            hit_slice_cap=True,
        )
        == CANONICAL_OUTCOME_PARTIAL_PROGRESS
    )


def test_classify_progressed() -> None:
    assert (
        _classify_drain_outcome(
            total_succeeded=10,
            total_failed_rows=0,
            topology_wait=False,
            candidate_more_remain=False,
            untreated_estimate=0,
            hit_slice_cap=False,
        )
        == CANONICAL_OUTCOME_PROGRESSED
    )


def test_classify_failed() -> None:
    assert (
        _classify_drain_outcome(
            total_succeeded=0,
            total_failed_rows=3,
            topology_wait=False,
            candidate_more_remain=True,
            untreated_estimate=10,
            hit_slice_cap=False,
        )
        == CANONICAL_OUTCOME_FAILED
    )


def test_classify_idle() -> None:
    assert (
        _classify_drain_outcome(
            total_succeeded=0,
            total_failed_rows=0,
            topology_wait=False,
            candidate_more_remain=False,
            untreated_estimate=0,
            hit_slice_cap=False,
        )
        == CANONICAL_OUTCOME_IDLE
    )


def test_pass_registry_nonempty() -> None:
    passes = all_canonical_passes()
    assert len(passes) > 0
    connectors = {p[0] for p in passes}
    assert "github" in connectors
    assert any(p[0] == "slack" and p[1] == "slack.message" for p in passes)


def test_pass_registry_slack_not_first() -> None:
    """Pass rotation must not assume first pass has rows (github precedes slack)."""
    passes = all_canonical_passes()
    assert passes[0][0] != "slack" or passes[0][1] != "slack.message"
