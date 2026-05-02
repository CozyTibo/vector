"""§6 Step 27 (+ §6 Step 42) — deterministic ``DecisionBundleItem`` ordering (no cap).

Sort key (stable, documented in code):

1. ``decision_type`` priority (safety / escalation first).
2. When ``signals.urgent_pressure == \"high\"``, ``blocker_not_tracked`` gaps sort earlier within
   the same decision-type band.
3. Combined gap order: ``gap_type_rank * STRIDE + learning_demotion`` (**§6 Step 42**; see
   ``decision_sort_learning``). ``STRIDE`` keeps zero-demotion ordering aligned with legacy
   ``gap_type`` priority; large demotions can move a gap later across bands. Omitted
   ``learning`` → demotion **0** everywhere.
4. ``decision.id`` (lexicographic tie-break).

§6 Step 28 applies ``max_decisions`` cap to this ordering; this step does **not** truncate.
"""

from __future__ import annotations

from vector.contracts.manager_insights_activity import (
    CoordinationDecisionType,
    DecisionBundle,
    DecisionBundleItem,
    DecisionItem,
    GapType,
    SignalsV0Debug,
)
from vector.domains.manager_insights.decision_sort_learning import DecisionSortLearning

# Upper bound for §6 Step 28 cap (query, env default, and applied slice).
MAX_DECISIONS_SURFACED_UPPER = 50


def resolve_max_decisions_surfaced(
    *,
    query_max: int | None,
    settings_default: int,
) -> int:
    """Integer cap: query overrides env default, clamped to 1..MAX_DECISIONS_SURFACED_UPPER."""
    raw = settings_default if query_max is None else query_max
    return max(1, min(int(raw), MAX_DECISIONS_SURFACED_UPPER))


def cap_prioritized_decisions(
    items: list[DecisionBundleItem],
    max_decisions: int,
) -> tuple[list[DecisionBundleItem], int]:
    """Truncate prioritized rows; preserves each ``DecisionBundleItem`` (including debug fields).

    Returns ``(truncated, len_before_cap)``.
    """
    before = len(items)
    m = max(1, min(max_decisions, MAX_DECISIONS_SURFACED_UPPER))
    return items[:m], before


# Lower = earlier in the surfaced list.
_DECISION_TYPE_RANK: dict[CoordinationDecisionType, int] = {
    "HOLD_START": 0,
    "BLOCKER_ESCALATION": 1,
    "RECENTER": 2,
    "PAUSE_INVESTMENT": 3,
    "CLARIFY_SPEC": 4,
    "LINK_OR_CLOSE_COMMITMENT": 5,
    "THREAD_TO_TRACKING_LINK": 6,
    "DOC_EXECUTION_BRIDGE": 7,
}

_GAP_TYPE_RANK: dict[GapType, int] = {
    "blocker_not_tracked": 0,
    "expected_not_executed": 1,
    "discussed_not_linked_to_work": 2,
    "doc_not_connected_to_execution": 3,
}

# §6 Step 42 — must stay **below** typical max demotion (~10.8k) so suppressed gaps can move
# past the next gap-type band while zero demotion keeps legacy gap-type order.
_GAP_RANK_LEARNING_STRIDE = 5_000


def _blocker_urgency_boost(decision: DecisionItem, signals: SignalsV0Debug | None) -> int:
    """0 = boost (sort earlier) when urgent pressure is high and gap is a blocker."""
    if signals is not None and signals.urgent_pressure == "high":
        if decision.gap_type == "blocker_not_tracked":
            return 0
    return 1


def _sort_tuple(
    row: DecisionBundleItem,
    signals: SignalsV0Debug | None,
) -> tuple[int, int, int, str]:
    d = row.decision
    return (
        _DECISION_TYPE_RANK[d.decision_type],
        _blocker_urgency_boost(d, signals),
        _GAP_TYPE_RANK[d.gap_type],
        d.id,
    )


def _gap_learning_sort_key(gap_type: GapType, learning: DecisionSortLearning | None) -> int:
    dem = 0 if learning is None else learning.demotion_for_gap_type(gap_type)
    return _GAP_TYPE_RANK[gap_type] * _GAP_RANK_LEARNING_STRIDE + dem


def _sort_tuple_with_learning(
    row: DecisionBundleItem,
    signals: SignalsV0Debug | None,
    learning: DecisionSortLearning | None,
) -> tuple[int, int, int, str]:
    d = row.decision
    return (
        _DECISION_TYPE_RANK[d.decision_type],
        _blocker_urgency_boost(d, signals),
        _gap_learning_sort_key(d.gap_type, learning),
        d.id,
    )


def prioritize_decisions(
    bundle: DecisionBundle,
    *,
    signals: SignalsV0Debug | None = None,
    learning: DecisionSortLearning | None = None,
) -> list[DecisionBundleItem]:
    """Return a new list of ``DecisionBundleItem`` rows in deterministic priority order.

    Does not mutate ``bundle``. Does **not** cap (§6 Step 28).

    When ``learning`` is omitted, §6 Step 42 contributes **0** demotion (legacy Step 27 order).
    """
    out = list(bundle.items)
    out.sort(key=lambda r: _sort_tuple_with_learning(r, signals, learning))
    return out


__all__ = [
    "MAX_DECISIONS_SURFACED_UPPER",
    "cap_prioritized_decisions",
    "prioritize_decisions",
    "resolve_max_decisions_surfaced",
]
