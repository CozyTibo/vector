"""§6 Steps 22–26 — deterministic gap → decision mapping (no LLM).

Base: each ``GapType`` → ``CoordinationDecisionType`` per coordination plan §2.3.

§6 Step 25: ``CLARIFY_SPEC`` / ``RECENTER`` / ``PAUSE_INVESTMENT`` from signals.

§6 Step 26: ``HOLD_START`` when scope is high **and** three guards pass (coordination plan §2.3):
high ambiguity signal, **no** ``decision``-kind evidence in the gap cluster, and open execution
work-item count **>** ``hold_start_affected_wi_threshold``. Cluster = BFS within link/perception
(+ optional execution-graph) adjacency up to ``HOLD_START_CLUSTER_HOPS``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from vector.contracts.manager_insights_activity import (
    CoordinationDecisionType,
    CoordinationLinkInputBundle,
    DecisionBundle,
    DecisionBundleItem,
    DecisionDefaultAction,
    DecisionEmissionTraceDebug,
    DecisionItem,
    DecisionRuleTraceDebug,
    EvidenceBundle,
    GapBundle,
    GapItem,
    GapType,
    LinkBundle,
    SignalsV0Debug,
    WorkItem,
    WorkItemBundle,
)
from vector.domains.manager_insights.build_execution_graph import build_execution_graph
from vector.domains.manager_insights.compute_gaps import (
    _adjacency,
    _execution_graph_undirected_adjacency,
    _merge_adjacency,
    _perception_mention_adjacency,
)

_GAP_TO_DECISION: dict[GapType, CoordinationDecisionType] = {
    "expected_not_executed": "LINK_OR_CLOSE_COMMITMENT",
    "discussed_not_linked_to_work": "THREAD_TO_TRACKING_LINK",
    "blocker_not_tracked": "BLOCKER_ESCALATION",
    "doc_not_connected_to_execution": "DOC_EXECUTION_BRIDGE",
}

_SCOPE_ELIGIBLE_GAP_TYPES: frozenset[GapType] = frozenset(
    {
        "discussed_not_linked_to_work",
        "doc_not_connected_to_execution",
        "expected_not_executed",
    }
)

_TITLE_TEMPLATE: dict[GapType, str] = {
    "expected_not_executed": "Link or close the commitment in tracking",
    "discussed_not_linked_to_work": "Link discussion to a tracked issue or PR",
    "blocker_not_tracked": "Track and escalate the blocker in execution systems",
    "doc_not_connected_to_execution": "Connect the document to tracked execution work",
}

_EXTENSION_TITLE: dict[CoordinationDecisionType, str] = {
    "CLARIFY_SPEC": "Clarify scope, constraints, and success criteria before continuing",
    "RECENTER": "Reconcile conflicting discussion and reset priorities",
    "PAUSE_INVESTMENT": "Pause incremental execution until scope and tradeoffs are aligned",
    "HOLD_START": "Hold starting new tracked work until scope is clarified",
}

_EXEC_TYPES = frozenset({"issue", "pull_request"})
_DONE_STATUS = frozenset(
    {
        "closed",
        "done",
        "completed",
        "complete",
        "merged",
        "cancelled",
        "canceled",
    }
)

# Bounded neighborhood for §6 Step 26 cluster (same adjacency as gap linking + optional graph).
HOLD_START_CLUSTER_HOPS = 3


def _is_execution_wi(w: WorkItem | None) -> bool:
    return bool(w and w.type in _EXEC_TYPES)


def _is_done_wi(w: WorkItem | None) -> bool:
    if w is None:
        return False
    if w.closed_at is not None:
        return True
    st = (w.status or "").strip().lower()
    return st in _DONE_STATUS


def _evidence_refs(gap: GapItem) -> list[str]:
    out: list[str] = []
    for _k, vals in sorted(gap.evidence_pointers.items()):
        out.extend(vals)
    seen: set[str] = set()
    unique: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            unique.append(x)
    return unique


def _signal_refs(signals: SignalsV0Debug) -> list[str]:
    """Non-low signal slots that may influence ordering in later steps (§6 Step 28)."""
    refs: list[str] = []
    if signals.urgent_pressure != "low":
        refs.append("urgent_pressure")
    if signals.scope_ambiguity != "low":
        refs.append("scope_ambiguity")
    if signals.discussion_churn != "low":
        refs.append("discussion_churn")
    if signals.contradiction_density != "low":
        refs.append("contradiction_density")
    if signals.repeated_discussion_present:
        refs.append("repeated_discussion_present")
    return refs


def _decision_id(gap: GapItem) -> str:
    return f"coordination:decision:{gap.id}"


def _gap_seed_work_items(gap: GapItem, by_id: dict[str, WorkItem]) -> set[str]:
    seeds: set[str] = set()
    for vals in gap.evidence_pointers.values():
        for ref in vals:
            if ref in by_id:
                seeds.add(ref)
    return seeds


def _cluster_bfs(seeds: set[str], adj: dict[str, set[str]], hops: int) -> set[str]:
    """Undirected BFS up to ``hops`` edge traversals from seeds."""
    if not seeds:
        return set()
    seen: set[str] = set(seeds)
    frontier: set[str] = set(seeds)
    for _ in range(hops):
        nxt: set[str] = set()
        for u in frontier:
            nxt |= adj.get(u, set())
        frontier = nxt - seen
        if not frontier:
            break
        seen |= frontier
    return seen


def _merged_adjacency(
    work_items: WorkItemBundle,
    links: LinkBundle,
    coordination_input: CoordinationLinkInputBundle,
    *,
    gaps_use_graph: bool,
) -> dict[str, set[str]]:
    by_id = {w.id: w for w in work_items.items}
    adj = _merge_adjacency(
        _adjacency(links),
        _perception_mention_adjacency(coordination_input.perception_rows, by_id),
    )
    if gaps_use_graph:
        exg = build_execution_graph(work_items, links, coordination_input)
        adj = _merge_adjacency(adj, _execution_graph_undirected_adjacency(exg))
    return adj


def _decision_evidence_ids_in_cluster(evidence: EvidenceBundle, cluster: set[str]) -> list[str]:
    return sorted({e.id for e in evidence.decisions if e.source_work_item_id in cluster})


def _open_execution_work_items(cluster: set[str], by_id: dict[str, WorkItem]) -> list[str]:
    out: list[str] = []
    for wid in sorted(cluster):
        w = by_id.get(wid)
        if _is_execution_wi(w) and not _is_done_wi(w):
            out.append(wid)
    return out


def _evaluate_hold_start_emission(
    gap: GapItem,
    sig: SignalsV0Debug,
    *,
    work_items: WorkItemBundle | None,
    links: LinkBundle | None,
    evidence: EvidenceBundle | None,
    coordination_input: CoordinationLinkInputBundle | None,
    hold_start_affected_wi_threshold: int,
    gaps_use_graph: bool,
) -> DecisionEmissionTraceDebug:
    scope_h = sig.scope_ambiguity == "high"
    base = DecisionEmissionTraceDebug(
        evaluated=True,
        inputs_complete=False,
        ambiguity_signal_high=scope_h,
        cluster_hops_used=HOLD_START_CLUSTER_HOPS,
        affected_wi_threshold=hold_start_affected_wi_threshold,
        guard_ambiguity_ok=scope_h,
        reason="",
    )
    if not scope_h:
        base.reason = "scope_ambiguity is not high; HOLD_START not considered."
        return base

    if gap.type not in _SCOPE_ELIGIBLE_GAP_TYPES:
        base.reason = "gap type not eligible for scope extension."
        return base

    if not (
        work_items is not None
        and links is not None
        and evidence is not None
        and coordination_input is not None
    ):
        base.reason = (
            "missing work_items/links/evidence/coordination_input; cannot evaluate cluster (CLARIFY_SPEC fallback)."
        )
        return base

    base.inputs_complete = True
    by_id = {w.id: w for w in work_items.items}
    seeds = _gap_seed_work_items(gap, by_id)
    base.seed_work_item_ids = sorted(seeds)
    if not seeds:
        base.reason = "no work item ids in gap.evidence_pointers resolved to WorkItemBundle; cannot form cluster."
        return base

    adj = _merged_adjacency(work_items, links, coordination_input, gaps_use_graph=gaps_use_graph)
    cluster = _cluster_bfs(seeds, adj, HOLD_START_CLUSTER_HOPS)
    base.cluster_work_item_ids = sorted(cluster)

    dec_ids = _decision_evidence_ids_in_cluster(evidence, cluster)
    base.decision_evidence_ids_in_cluster = dec_ids
    base.guard_no_decision_evidence_in_cluster_ok = len(dec_ids) == 0

    open_exec = _open_execution_work_items(cluster, by_id)
    base.open_execution_work_item_ids = open_exec
    base.open_execution_count = len(open_exec)
    base.guard_open_execution_count_ok = base.open_execution_count > hold_start_affected_wi_threshold

    if base.guard_ambiguity_ok and base.guard_no_decision_evidence_in_cluster_ok and base.guard_open_execution_count_ok:
        base.hold_start_emitted = True
        base.reason = (
            f"HOLD_START: open_execution_count={base.open_execution_count} "
            f"> threshold={hold_start_affected_wi_threshold}; no decision evidence in cluster."
        )
    else:
        parts: list[str] = []
        if not base.guard_no_decision_evidence_in_cluster_ok:
            parts.append(f"decision evidence in cluster: {dec_ids}")
        if not base.guard_open_execution_count_ok:
            parts.append(
                f"open_execution_count={base.open_execution_count} "
                f"not > threshold={hold_start_affected_wi_threshold}"
            )
        base.reason = "CLARIFY_SPEC fallback: " + "; ".join(parts) if parts else "CLARIFY_SPEC fallback."

    return base


def _resolve_decision(
    gap: GapItem,
    sig: SignalsV0Debug | None,
    *,
    work_items: WorkItemBundle | None,
    links: LinkBundle | None,
    evidence: EvidenceBundle | None,
    coordination_input: CoordinationLinkInputBundle | None,
    hold_start_affected_wi_threshold: int,
    gaps_use_graph: bool,
) -> tuple[CoordinationDecisionType, str, DecisionEmissionTraceDebug | None]:
    base = _GAP_TO_DECISION[gap.type]
    base_rule = f"gap:{gap.type}:v1"
    if sig is None:
        return base, base_rule, None

    churn_h = sig.discussion_churn == "high"
    contra_h = sig.contradiction_density == "high"
    if contra_h and churn_h:
        if gap.type == "discussed_not_linked_to_work":
            return "RECENTER", "extension:recenter_contradiction_churn:v1", None
        if gap.type == "expected_not_executed":
            return "PAUSE_INVESTMENT", "extension:pause_investment_contradiction_churn:v1", None
        if gap.type == "doc_not_connected_to_execution":
            return "RECENTER", "extension:recenter_contradiction_churn:v1", None

    scope_h = sig.scope_ambiguity == "high"
    if scope_h and gap.type in _SCOPE_ELIGIBLE_GAP_TYPES:
        emission = _evaluate_hold_start_emission(
            gap,
            sig,
            work_items=work_items,
            links=links,
            evidence=evidence,
            coordination_input=coordination_input,
            hold_start_affected_wi_threshold=hold_start_affected_wi_threshold,
            gaps_use_graph=gaps_use_graph,
        )
        if emission.hold_start_emitted:
            return "HOLD_START", "extension:hold_start_scope_cluster:v1", emission
        return "CLARIFY_SPEC", "extension:clarify_spec_scope_high:v1", emission

    return base, base_rule, None


def _title_for(decision_type: CoordinationDecisionType, gap_type: GapType) -> str:
    if decision_type in _EXTENSION_TITLE:
        return _EXTENSION_TITLE[decision_type]
    return _TITLE_TEMPLATE[gap_type]


def _rationale(
    gap: GapItem,
    decision_type: CoordinationDecisionType,
    matched_rule: str,
    sig: SignalsV0Debug | None,
    emission: DecisionEmissionTraceDebug | None,
) -> str:
    if decision_type == "HOLD_START" and emission is not None:
        return (
            f"Gap {gap.id} ({gap.type}): {gap.description}. "
            f"HOLD_START via {matched_rule} (§6 Step 26; coordination plan §2.3). "
            f"{emission.reason}"
        )
    if matched_rule.startswith("extension:") and sig is not None:
        extra = ""
        if emission is not None and emission.evaluated and not emission.hold_start_emitted:
            extra = f" Emission trace: {emission.reason}"
        return (
            f"Gap {gap.id} ({gap.type}): {gap.description}. "
            f"Template {decision_type} via {matched_rule} "
            f"(§6 Step 25; coordination plan §2.3 extensions). "
            f"Signals: scope_ambiguity={sig.scope_ambiguity}, "
            f"discussion_churn={sig.discussion_churn}, "
            f"contradiction_density={sig.contradiction_density}.{extra}"
        )
    return (
        f"Gap {gap.id} ({gap.type}): {gap.description} "
        f"(§6 Step 22; coordination §2.3 base mapping)."
    )


def compute_decisions(
    gaps: GapBundle,
    *,
    signals: SignalsV0Debug | None = None,
    work_items: WorkItemBundle | None = None,
    links: LinkBundle | None = None,
    evidence: EvidenceBundle | None = None,
    coordination_input: CoordinationLinkInputBundle | None = None,
    hold_start_affected_wi_threshold: int = 2,
    gaps_use_graph_adjacency: bool = False,
    created_at: datetime | None = None,
    include_decision_debug: bool = True,
) -> DecisionBundle:
    """Build a ``DecisionBundle`` with one row per gap (deterministic templates).

    Pass ``work_items`` … ``coordination_input`` so §6 Step 26 can evaluate ``HOLD_START``; when omitted,
    scope-high rows fall back to ``CLARIFY_SPEC`` with an emission trace explaining missing inputs.
    """
    ts = created_at or datetime.now(UTC)
    sig = signals
    items: list[DecisionBundleItem] = []
    for gap in gaps.gaps:
        d_type, matched_rule, emission = _resolve_decision(
            gap,
            sig,
            work_items=work_items,
            links=links,
            evidence=evidence,
            coordination_input=coordination_input,
            hold_start_affected_wi_threshold=hold_start_affected_wi_threshold,
            gaps_use_graph=gaps_use_graph_adjacency,
        )
        title = _title_for(d_type, gap.type)
        rationale = _rationale(gap, d_type, matched_rule, sig, emission)
        decision = DecisionItem(
            id=_decision_id(gap),
            gap_id=gap.id,
            gap_type=gap.type,
            decision_type=d_type,
            title=title,
            rationale=rationale,
            default_action=DecisionDefaultAction(kind="noop"),
            required_inputs={},
            evidence_refs=_evidence_refs(gap),
            signal_refs=_signal_refs(sig) if sig is not None else [],
            created_at=ts,
            run_id=gaps.run_id,
            status=None,
        )
        dbg: DecisionRuleTraceDebug | None = None
        emission_out: DecisionEmissionTraceDebug | None = None
        if include_decision_debug:
            ext = matched_rule.startswith("extension:")
            dbg = DecisionRuleTraceDebug(
                gap_id=gap.id,
                matched_rule=matched_rule,
                conditions_met={
                    "gap_present": True,
                    "extension_route": ext,
                    "scope_ambiguity_high": bool(sig and sig.scope_ambiguity == "high"),
                    "discussion_churn_high": bool(sig and sig.discussion_churn == "high"),
                    "contradiction_density_high": bool(sig and sig.contradiction_density == "high"),
                    "hold_start_emitted": bool(emission and emission.hold_start_emitted),
                },
            )
            emission_out = emission
        items.append(
            DecisionBundleItem(
                decision=decision,
                decision_debug=dbg,
                decision_emission_debug=emission_out,
            )
        )
    return DecisionBundle(
        run_id=gaps.run_id,
        tenant_id=gaps.tenant_id,
        window_days=gaps.window_days,
        items=items,
    )
