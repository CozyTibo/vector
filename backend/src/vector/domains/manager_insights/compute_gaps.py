"""Step 5 — Deterministic gap computation from work items + evidence + links.

§6 Step 13: ``compute_gaps`` takes the same ``CoordinationLinkInputBundle`` as ``link_work_items``
(validated ``PerceptionRow`` + Step-3 evidence). When ``perception_rows`` is empty, behavior matches
the pre–Step 13 path (link adjacency only). Non-empty rows add **mention adjacency**: undirected edges
when another work item id (substring containing ``:``) appears in grounded perception text, so
``_linked_execution_ids`` can see execution neighbors without duplicating raw LLM JSON.
"""

from __future__ import annotations

import hashlib

from vector.contracts.manager_insights_activity import (
    CoordinationLinkInputBundle,
    EvidenceItem,
    ExecutionGraph,
    GapBundle,
    GapItem,
    GapType,
    LinkBundle,
    LinkConfidence,
    PerceptionRow,
    WorkItem,
    WorkItemBundle,
)
from vector.domains.manager_insights.build_execution_graph import build_execution_graph

_EXEC_TYPES = {"issue", "pull_request"}
_LINK_CONFIDENCE_ALLOWED: set[LinkConfidence] = {"high", "medium"}
_DONE_STATUS = {
    "closed",
    "done",
    "completed",
    "complete",
    "merged",
    "cancelled",
    "canceled",
}


def _gap_id(gap_type: GapType, refs: list[str]) -> str:
    raw = f"{gap_type}|{'|'.join(sorted(refs))}"
    d = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"gap:{d}"


def _is_execution_item(w: WorkItem | None) -> bool:
    return bool(w and w.type in _EXEC_TYPES)


def _is_done(w: WorkItem | None) -> bool:
    if w is None:
        return False
    if w.closed_at is not None:
        return True
    st = (w.status or "").strip().lower()
    return st in _DONE_STATUS


def _adjacency(links: LinkBundle) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for e in links.links:
        if e.confidence not in _LINK_CONFIDENCE_ALLOWED:
            continue
        out.setdefault(e.from_work_item_id, set()).add(e.to_work_item_id)
        out.setdefault(e.to_work_item_id, set()).add(e.from_work_item_id)
    return out


def _execution_graph_undirected_adjacency(graph: ExecutionGraph) -> dict[str, set[str]]:
    """§6 Step 18 — treat each execution graph edge as an undirected 1-hop link between endpoints."""
    out: dict[str, set[str]] = {}
    for e in graph.edges:
        out.setdefault(e.from_id, set()).add(e.to_id)
        out.setdefault(e.to_id, set()).add(e.from_id)
    return out


def _merge_adjacency(
    a: dict[str, set[str]],
    b: dict[str, set[str]],
) -> dict[str, set[str]]:
    keys = set(a) | set(b)
    out: dict[str, set[str]] = {}
    for k in keys:
        merged = a.get(k, set()) | b.get(k, set())
        if merged:
            out[k] = merged
    return out


def _perception_mention_adjacency(
    rows: list[PerceptionRow],
    by_id: dict[str, WorkItem],
) -> dict[str, set[str]]:
    """Edges when perception text (validated rows only) mentions another work item id as substring."""
    if not rows:
        return {}
    out: dict[str, set[str]] = {}
    # Longer ids first so e.g. linear:issue:abc wins over accidental short overlaps.
    sorted_ids = sorted(by_id.keys(), key=len, reverse=True)
    for row in rows:
        parts: list[str] = [row.statement, row.quote]
        if row.ambiguity_quote and row.ambiguity_quote.strip():
            parts.append(row.ambiguity_quote)
        if row.state_transition is not None:
            parts.append(row.state_transition.quote)
        parts.extend(row.waits_on or [])
        parts.extend(row.blocked_by or [])
        blob = " ".join(p for p in parts if p)
        src = row.work_item_id
        for wid in sorted_ids:
            if wid == src:
                continue
            # Require ':' to match canonical cross-tool ids (call:x, linear:issue:y, …).
            if ":" not in wid:
                continue
            if wid in blob:
                out.setdefault(src, set()).add(wid)
                out.setdefault(wid, set()).add(src)
    return out


def _linked_execution_ids(
    row: EvidenceItem,
    adj: dict[str, set[str]],
    by_id: dict[str, WorkItem],
) -> list[str]:
    ids: set[str] = set()
    for i in row.linked_work_items:
        w = by_id.get(i)
        if _is_execution_item(w):
            ids.add(i)
    for i in adj.get(row.source_work_item_id, set()):
        w = by_id.get(i)
        if _is_execution_item(w):
            ids.add(i)
    return sorted(ids)


def compute_gaps(
    work_items: WorkItemBundle,
    links: LinkBundle,
    coordination_input: CoordinationLinkInputBundle,
    *,
    gaps_use_graph: bool = False,
) -> GapBundle:
    """Compute V0 gaps (no LLM): expected vs actual, discussed-not-linked, blockers, docs linkage.

    §6 Step 13: use ``coordination_input.evidence`` and merge link adjacency with
    ``_perception_mention_adjacency`` when ``coordination_input.perception_rows`` is non-empty.

    §6 Step 18: when ``gaps_use_graph`` is true, merge undirected 1-hop neighbors from
    ``build_execution_graph`` (references + perception depends_on/blocks edges).
    """
    evidence = coordination_input.evidence
    by_id = {w.id: w for w in work_items.items}
    adj = _merge_adjacency(
        _adjacency(links),
        _perception_mention_adjacency(coordination_input.perception_rows, by_id),
    )
    gaps_debug: str | None = None
    if gaps_use_graph:
        exg = build_execution_graph(work_items, links, coordination_input)
        adj = _merge_adjacency(adj, _execution_graph_undirected_adjacency(exg))
        n_edges = len(exg.edges)
        gaps_debug = (
            f"§6 Step 18: merged execution-graph 1-hop adjacency ({n_edges} graph edges into gap neighborhood)."
        )
    gaps: list[GapItem] = []
    seen: set[tuple[GapType, str]] = set()

    def add_gap(gtype: GapType, primary_ref: str, description: str, pointers: dict[str, list[str]]) -> None:
        key = (gtype, primary_ref)
        if key in seen:
            return
        seen.add(key)
        refs = [primary_ref]
        for vals in pointers.values():
            refs.extend(vals)
        gaps.append(
            GapItem(
                id=_gap_id(gtype, refs),
                type=gtype,
                description=description,
                evidence_pointers={k: sorted(set(v)) for k, v in pointers.items()},
            )
        )

    # 1) expected_not_executed: action item has no linked execution item OR only non-done execution.
    for a in evidence.action_items:
        exec_ids = _linked_execution_ids(a, adj, by_id)
        done_exec_ids = [i for i in exec_ids if _is_done(by_id.get(i))]
        if done_exec_ids:
            continue
        add_gap(
            "expected_not_executed",
            a.id,
            "Action item has no linked closed issue or merged PR in tracked systems.",
            {
                "action_item_ids": [a.id],
                "source_work_item_ids": [a.source_work_item_id],
                "linked_execution_item_ids": exec_ids,
            },
        )

    # 2) discussed_not_linked_to_work: discussed evidence item has no linked execution work.
    for row in [*evidence.action_items, *evidence.decisions]:
        exec_ids = _linked_execution_ids(row, adj, by_id)
        if exec_ids:
            continue
        add_gap(
            "discussed_not_linked_to_work",
            row.id,
            "Discussion evidence is not linked to any tracked issue or PR.",
            {
                "evidence_item_ids": [row.id],
                "source_work_item_ids": [row.source_work_item_id],
            },
        )

    # 3) blocker_not_tracked: blocker exists but no issue/PR is linked.
    for b in evidence.blockers:
        exec_ids = _linked_execution_ids(b, adj, by_id)
        if exec_ids:
            continue
        add_gap(
            "blocker_not_tracked",
            b.id,
            "Blocker is mentioned but not linked to a tracked issue/PR.",
            {
                "blocker_item_ids": [b.id],
                "source_work_item_ids": [b.source_work_item_id],
            },
        )

    # 4) doc_not_connected_to_execution: docs with no medium/high edge to issue/PR.
    for wi in work_items.items:
        if wi.type != "document":
            continue
        exec_neighbors = [
            n for n in sorted(adj.get(wi.id, set())) if _is_execution_item(by_id.get(n))
        ]
        if exec_neighbors:
            continue
        add_gap(
            "doc_not_connected_to_execution",
            wi.id,
            "Document has no medium/high-confidence link to tracked issue or PR.",
            {
                "document_work_item_ids": [wi.id],
            },
        )

    gaps.sort(key=lambda g: (g.type, g.id))
    return GapBundle(
        run_id=work_items.run_id,
        tenant_id=work_items.tenant_id,
        window_days=work_items.window_days,
        gaps=gaps,
        gaps_debug=gaps_debug,
    )

