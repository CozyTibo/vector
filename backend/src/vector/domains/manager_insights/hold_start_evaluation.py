"""§6 Step 26 — HOLD_START cluster evaluation (shared by situation + legacy paths)."""

from __future__ import annotations

from vector.contracts.manager_insights_activity import (
    CoordinationLinkInputBundle,
    DecisionEmissionTraceDebug,
    EvidenceBundle,
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

SCOPE_ELIGIBLE_GAP_TYPES: frozenset[GapType] = frozenset(
    {
        "discussed_not_linked_to_work",
        "doc_not_connected_to_execution",
        "expected_not_executed",
    }
)

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


def _gap_seed_work_items(gap: GapItem, by_id: dict[str, WorkItem]) -> set[str]:
    seeds: set[str] = set()
    for vals in gap.evidence_pointers.values():
        for ref in vals:
            if ref in by_id:
                seeds.add(ref)
    return seeds


def _cluster_bfs(seeds: set[str], adj: dict[str, set[str]], hops: int) -> set[str]:
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


def evaluate_hold_start_emission(
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

    if gap.type not in SCOPE_ELIGIBLE_GAP_TYPES:
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


__all__ = ["evaluate_hold_start_emission", "HOLD_START_CLUSTER_HOPS", "SCOPE_ELIGIBLE_GAP_TYPES"]
