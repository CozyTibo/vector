"""§6 Step 6.6 — compose a dominant execution situation + supporting situations (deterministic narrative)."""

from __future__ import annotations

from dataclasses import dataclass

from vector.contracts.manager_insights_activity import (
    ExecutionSituation,
    ExecutionSituationType,
    SignalsV0Debug,
)
from vector.domains.manager_insights.detect_execution_situations import (
    ACTOR_COORDINATION_SITUATION_TYPES,
    situation_axis_key,
    situation_gap_jaccard,
)


def _cross_signal_density(s: ExecutionSituation) -> float:
    return min(1.0, len({x for x in s.supporting_signals}) / 8.0)


def _cross_gap_coverage(s: ExecutionSituation, total_gaps: int) -> float:
    return min(1.0, len(s.supporting_gap_ids) / max(1, total_gaps))


def _situation_key(s: ExecutionSituation) -> str:
    return f"{s.type}:{s.decision_override or ''}"


def _active_themes(
    types_present: set[ExecutionSituationType],
    sig: SignalsV0Debug,
) -> list[tuple[str, frozenset[ExecutionSituationType]]]:
    out: list[tuple[str, frozenset[ExecutionSituationType]]] = []
    if {"INVISIBLE_BLOCKERS", "DECISION_LOOP"} <= types_present:
        out.append(("coordination_breakdown", frozenset({"INVISIBLE_BLOCKERS", "DECISION_LOOP"})))
    if {"FRAGMENTED_EXECUTION", "PRIORITY_CONFLICT"} <= types_present:
        out.append(("lack_of_focus", frozenset({"FRAGMENTED_EXECUTION", "PRIORITY_CONFLICT"})))
    if {"MISALIGNED_REALITY", "SCOPE_DRIFT"} <= types_present:
        out.append(("execution_confusion", frozenset({"MISALIGNED_REALITY", "SCOPE_DRIFT"})))
    # REVIEW_BOTTLENECK + momentum slowing (signal) or FRAGMENTED as WIP/momentum proxy
    if "REVIEW_BOTTLENECK" in types_present and "FRAGMENTED_EXECUTION" in types_present:
        out.append(("delivery_friction", frozenset({"REVIEW_BOTTLENECK", "FRAGMENTED_EXECUTION"})))
    elif "REVIEW_BOTTLENECK" in types_present and sig.execution_momentum == "slowing":
        out.append(("delivery_friction", frozenset({"REVIEW_BOTTLENECK"})))
    return out


def _explains_boost(s: ExecutionSituation, themes: list[tuple[str, frozenset[ExecutionSituationType]]]) -> float:
    boost = 0.0
    for _name, members in themes:
        if s.type in members:
            boost += 0.12
    return boost


def _actor_situation_narrative_boost(s: ExecutionSituation) -> float:
    return 0.24 if s.type in ACTOR_COORDINATION_SITUATION_TYPES else 0.0


def _overlap_boost(s: ExecutionSituation, sit_list: list[ExecutionSituation]) -> float:
    others = [x for x in sit_list if _situation_key(x) != _situation_key(s)]
    n = sum(1 for o in others if situation_gap_jaccard(s.supporting_gap_ids, o.supporting_gap_ids) >= 0.25)
    if n >= 2:
        return 0.22
    if n == 1:
        return 0.09
    return 0.0


def _reinforces(
    s: ExecutionSituation,
    dominant: ExecutionSituation,
    themes: list[tuple[str, frozenset[ExecutionSituationType]]],
) -> float:
    if situation_gap_jaccard(s.supporting_gap_ids, dominant.supporting_gap_ids) >= 0.2:
        return 1.0
    for _name, members in themes:
        if s.type in members and dominant.type in members:
            return 0.85
    return 0.0


@dataclass(frozen=True)
class ExecutionNarrative:
    """Ordered narrative: one headline situation + up to four supporting situations."""

    dominant: ExecutionSituation
    supporting: tuple[ExecutionSituation, ...]
    theme: str | None
    relationship_labels: tuple[str, ...]


def compose_execution_narrative(
    situations: list[ExecutionSituation],
    *,
    signals: SignalsV0Debug,
    total_gap_count: int,
) -> ExecutionNarrative:
    """Select dominant + supporting situations using severity, signal density, gap coverage, and reinforcement."""
    if not situations:
        msg = "compose_execution_narrative requires at least one situation"
        raise ValueError(msg)

    sit_list = list(situations)
    types_present: set[ExecutionSituationType] = set()
    for s in sit_list:
        types_present.add(s.type)
        types_present.update(s.aggregated_supporting_situation_types)
    themes = _active_themes(types_present, signals)

    scores: dict[str, float] = {}
    for s in sit_list:
        k = _situation_key(s)
        base = s.severity * (0.45 + 0.55 * _cross_signal_density(s)) * (0.45 + 0.55 * _cross_gap_coverage(s, total_gap_count))
        sc = base + _explains_boost(s, themes) + _overlap_boost(s, sit_list) + _actor_situation_narrative_boost(s)
        scores[k] = max(scores.get(k, 0.0), sc)

    dominant = max(sit_list, key=lambda s: (scores[_situation_key(s)], s.severity, s.type))

    theme: str | None = None
    for name, members in themes:
        if dominant.type in members and members <= types_present:
            theme = name
            break
    if theme is None:
        for name, members in themes:
            if members <= types_present:
                theme = name
                break

    rel_labels: list[str] = []
    for name, members in themes:
        if members <= types_present:
            rel_labels.append(f"{name}:{','.join(sorted(members))}")

    others = [s for s in sit_list if _situation_key(s) != _situation_key(dominant)]
    dom_axis = situation_axis_key(dominant)[0]

    scored_support: list[tuple[float, float, ExecutionSituation]] = []
    for s in others:
        if situation_axis_key(s)[0] == dom_axis:
            continue
        rf = _reinforces(s, dominant, themes)
        if rf <= 0 and situation_gap_jaccard(s.supporting_gap_ids, dominant.supporting_gap_ids) < 0.1:
            continue
        scored_support.append((rf, s.severity, s))

    scored_support.sort(key=lambda t: (-t[0], -t[1], t[2].type))
    picked: list[ExecutionSituation] = [t[2] for t in scored_support[:4]]

    if len(picked) < 2 and len(others) >= 2:
        for s in sorted(others, key=lambda x: (-x.severity, x.type)):
            if s in picked:
                continue
            if situation_axis_key(s)[0] == dom_axis:
                continue
            picked.append(s)
            if len(picked) >= 2:
                break

    supporting = tuple(picked[:4])
    return ExecutionNarrative(
        dominant=dominant,
        supporting=supporting,
        theme=theme,
        relationship_labels=tuple(rel_labels),
    )


def compose_execution_narrative_from_ordered(
    dominant: ExecutionSituation,
    supporting: tuple[ExecutionSituation, ...],
    *,
    signals: SignalsV0Debug,
    total_gap_count: int,
) -> ExecutionNarrative:
    """Build narrative metadata when dominant + supporting order is fixed (e.g. cross-failure dominance)."""
    sit_list = [dominant, *supporting]
    types_present: set[ExecutionSituationType] = set()
    for s in sit_list:
        types_present.add(s.type)
        types_present.update(s.aggregated_supporting_situation_types)
    themes = _active_themes(types_present, signals)

    theme: str | None = None
    for name, members in themes:
        if dominant.type in members and members <= types_present:
            theme = name
            break
    if theme is None:
        for name, members in themes:
            if members <= types_present:
                theme = name
                break

    rel_labels: list[str] = []
    for name, members in themes:
        if members <= types_present:
            rel_labels.append(f"{name}:{','.join(sorted(members))}")

    return ExecutionNarrative(
        dominant=dominant,
        supporting=supporting,
        theme=theme,
        relationship_labels=tuple(rel_labels),
    )


__all__ = [
    "ExecutionNarrative",
    "compose_execution_narrative",
    "compose_execution_narrative_from_ordered",
]
