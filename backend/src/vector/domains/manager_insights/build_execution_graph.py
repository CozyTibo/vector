"""§6 Step 15 — ephemeral execution graph from work items, links, and validated perception."""

from __future__ import annotations

import hashlib

from vector.contracts.manager_insights_activity import (
    CoordinationLinkInputBundle,
    ExecutionEdge,
    ExecutionGraph,
    ExecutionGraphEdgeRelation,
    ExecutionGraphNodeKind,
    ExecutionNode,
    ExecutionStatePerception,
    LinkBundle,
    WorkItem,
    WorkItemBundle,
)

_LINK_OK = frozenset({"high", "medium"})
_DONE = frozenset(
    {"done", "closed", "merged", "completed", "complete", "canceled", "cancelled"}
)


def _node_kind(wi: WorkItem) -> ExecutionGraphNodeKind:
    if wi.type == "pull_request":
        return "pr"
    if wi.type == "document":
        return "doc"
    if wi.type in ("call", "message_thread"):
        return "thread"
    return "issue"


def _derive_state(wi: WorkItem) -> ExecutionStatePerception | None:
    if wi.closed_at is not None:
        return "done"
    st = (wi.status or "").strip().lower()
    if st in _DONE:
        return "done"
    if wi.type in ("issue", "pull_request"):
        return "in_progress"
    return None


def _edge_id(a: str, b: str, relation: ExecutionGraphEdgeRelation) -> str:
    raw = f"{a}|{b}|{relation}"
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"exec_edge:{h}"


def _sorted_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def _resolve_ids_in_entry(entry: str, sorted_ids: list[str]) -> list[str]:
    """Match work item ids (must contain ':') as substrings of entry."""
    if not entry.strip():
        return []
    out: list[str] = []
    for wid in sorted_ids:
        if ":" not in wid:
            continue
        if wid in entry:
            out.append(wid)
    return out


def build_execution_graph(
    work_items: WorkItemBundle,
    links: LinkBundle,
    coordination_input: CoordinationLinkInputBundle,
) -> ExecutionGraph:
    """Build a pure, ephemeral execution graph (coordination Step 4.5).

    - **Nodes:** one per ``WorkItem``; state from perception when available else derived from WI.
    - **Edges:** ``references`` from medium/high links; ``depends_on`` / ``blocks`` from grounded
      perception lists when targets resolve to known work item ids.
    - **Unresolved** dependency strings are recorded **only** in ``unresolved_dependency_refs`` —
      they never become edges (architecture lock).
    """
    by_id: dict[str, WorkItem] = {w.id: w for w in work_items.items}
    sorted_ids = sorted(by_id.keys(), key=len, reverse=True)

    perception_by_wi: dict[str, PerceptionRow] = {}
    for row in coordination_input.perception_rows:
        perception_by_wi[row.work_item_id] = row

    nodes: list[ExecutionNode] = []
    for wi in work_items.items:
        pr = perception_by_wi.get(wi.id)
        state = pr.execution_state if pr is not None else _derive_state(wi)
        owner = None
        if pr is not None and pr.ownership_inferred is not None:
            owner = pr.ownership_inferred.text_span.strip()
            if pr.ownership_inferred.role_guess:
                owner = f"{owner} ({pr.ownership_inferred.role_guess})"
        nodes.append(
            ExecutionNode(
                id=wi.id,
                kind=_node_kind(wi),
                execution_state=state,
                owner_hint=owner or None,
            )
        )

    edges: list[ExecutionEdge] = []
    seen: set[tuple[str, str, ExecutionGraphEdgeRelation]] = set()

    def add_edge(
        from_id: str,
        to_id: str,
        relation: ExecutionGraphEdgeRelation,
        *,
        dedupe_key: tuple[str, str, ExecutionGraphEdgeRelation],
    ) -> None:
        if from_id not in by_id or to_id not in by_id or from_id == to_id:
            return
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        edges.append(
            ExecutionEdge(
                id=_edge_id(from_id, to_id, relation),
                from_id=from_id,
                to_id=to_id,
                relation=relation,
            )
        )

    # Links → references (canonical undirected pair, single stored edge from_id < to_id)
    for lk in links.links:
        if lk.confidence not in _LINK_OK:
            continue
        a, b = _sorted_pair(lk.from_work_item_id, lk.to_work_item_id)
        add_edge(a, b, "references", dedupe_key=(a, b, "references"))

    unresolved: list[str] = []

    for row in coordination_input.perception_rows:
        src = row.work_item_id
        if src not in by_id:
            continue

        for entry in row.waits_on or []:
            matched = _resolve_ids_in_entry(entry, sorted_ids)
            if not matched:
                if entry.strip():
                    unresolved.append(f"{src}|waits_on|{entry.strip()}")
                continue
            for tid in matched:
                if tid == src:
                    continue
                add_edge(src, tid, "depends_on", dedupe_key=(src, tid, "depends_on"))

        for entry in row.blocked_by or []:
            matched = _resolve_ids_in_entry(entry, sorted_ids)
            if not matched:
                if entry.strip():
                    unresolved.append(f"{src}|blocked_by|{entry.strip()}")
                continue
            for blocker in matched:
                if blocker == src:
                    continue
                add_edge(blocker, src, "blocks", dedupe_key=(blocker, src, "blocks"))

    nodes.sort(key=lambda n: n.id)
    edges.sort(key=lambda e: (e.relation, e.from_id, e.to_id))
    unresolved_sorted = sorted(set(unresolved))

    return ExecutionGraph(
        run_id=work_items.run_id,
        tenant_id=work_items.tenant_id,
        window_days=work_items.window_days,
        nodes=nodes,
        edges=edges,
        unresolved_dependency_refs=unresolved_sorted,
    )


__all__ = ["build_execution_graph"]
