"""Pass-local fairness for canonical forward-progress."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from vector.domains.cortex.canonical.forward_progress.drain_runtime import _classify_drain_outcome
from vector.domains.cortex.canonical.forward_progress.constants import (
    CANONICAL_OUTCOME_PARTIAL_PROGRESS,
    CANONICAL_OUTCOME_TOPOLOGY_WAIT,
)
from vector.domains.cortex.canonical.forward_progress.pass_fairness import (
    parse_pass_cooldown_until,
    record_pass_topology_stall,
    resolve_fair_pass_cursor,
    serialize_pass_cooldown_until,
)
from vector.domains.cortex.canonical.forward_progress.pass_registry import (
    all_canonical_passes,
    all_canonical_passes_fair_rotation,
)


def test_fair_rotation_interleaves_connectors() -> None:
    fair = all_canonical_passes_fair_rotation()
    flat = all_canonical_passes()
    assert len(fair) == len(flat)
    connectors = [p[0] for p in fair[:6]]
    assert len(set(connectors)) > 1


def test_resolve_pass_cursor_skips_cooled_pass() -> None:
    passes = all_canonical_passes_fair_rotation()
    assert passes
    first_key = f"{passes[0][0]}/{passes[0][1]}"
    now = datetime.now(UTC)
    cooldowns = {first_key: now + timedelta(hours=1)}
    _c, _rt, pk, _nxt, skipped = resolve_fair_pass_cursor(0, pass_cooldowns=cooldowns, now=now)
    assert skipped is True
    assert pk != first_key


def test_record_pass_topology_stall_escalates() -> None:
    now = datetime.now(UTC)
    cooldowns: dict[str, datetime] = {}
    stalls: dict[str, int] = {}
    record_pass_topology_stall(
        pass_key="github/pull_request_timeline_event",
        pass_cooldowns=cooldowns,
        pass_stall_counts=stalls,
        base_cooldown_seconds=90,
        max_cooldown_seconds=360,
        now=now,
    )
    record_pass_topology_stall(
        pass_key="github/pull_request_timeline_event",
        pass_cooldowns=cooldowns,
        pass_stall_counts=stalls,
        base_cooldown_seconds=90,
        max_cooldown_seconds=360,
        now=now,
    )
    assert stalls["github/pull_request_timeline_event"] == 2
    assert cooldowns["github/pull_request_timeline_event"] > now + timedelta(seconds=170)


def test_parse_serialize_pass_cooldown_roundtrip() -> None:
    now = datetime.now(UTC)
    raw = serialize_pass_cooldown_until({"notion/database_row": now})
    parsed = parse_pass_cooldown_until({"pass_cooldown_until": raw})
    assert "notion/database_row" in parsed


def test_classify_partial_when_topology_stall_but_succeeded() -> None:
    assert (
        _classify_drain_outcome(
            total_succeeded=120,
            total_failed_rows=0,
            full_rotation_topology_stall=True,
            candidate_more_remain=True,
            untreated_estimate=5000,
            hit_slice_cap=True,
        )
        == CANONICAL_OUTCOME_PARTIAL_PROGRESS
    )


def test_classify_topology_wait_only_when_stalled_with_no_success() -> None:
    assert (
        _classify_drain_outcome(
            total_succeeded=0,
            total_failed_rows=0,
            full_rotation_topology_stall=True,
            candidate_more_remain=True,
            untreated_estimate=1000,
            hit_slice_cap=False,
        )
        == CANONICAL_OUTCOME_TOPOLOGY_WAIT
    )
