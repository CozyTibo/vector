"""§6 Step 15 — ExecutionGraph + build_execution_graph."""

from __future__ import annotations

import uuid

from vector.contracts.manager_insights_activity import (
    CoordinationLinkInputBundle,
    EvidenceBundle,
    ExecutionGraph,
    LinkBundle,
    PerceptionOwnershipInferred,
    PerceptionRow,
    WorkItem,
    WorkItemBundle,
    WorkItemLink,
)
from vector.domains.manager_insights.build_execution_graph import build_execution_graph


def _wi(**kwargs: object) -> WorkItem:
    return WorkItem(
        id=kwargs["id"],  # type: ignore[arg-type]
        source=kwargs["source"],  # type: ignore[arg-type]
        type=kwargs["type"],  # type: ignore[arg-type]
        title=kwargs["title"],  # type: ignore[arg-type]
        summary=kwargs.get("summary"),
        status=kwargs.get("status"),
        source_ref={},
    )


def _empty_evidence(bundle: WorkItemBundle) -> EvidenceBundle:
    return EvidenceBundle(
        run_id=bundle.run_id,
        tenant_id=bundle.tenant_id,
        window_days=bundle.window_days,
        action_items=[],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )


def test_graph_round_trip_json() -> None:
    g = ExecutionGraph(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        nodes=[],
        edges=[],
        unresolved_dependency_refs=[],
    )
    data = g.model_dump(mode="json")
    assert ExecutionGraph.model_validate(data) == g


def test_link_produces_references_edge_only_between_known_nodes() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    bundle = WorkItemBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            _wi(
                id="a:1",
                source="calls",
                type="call",
                title="Call",
            ),
            _wi(
                id="b:2",
                source="linear",
                type="issue",
                title="Issue",
            ),
        ],
    )
    links = LinkBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        links=[
            WorkItemLink(
                id="l1",
                from_work_item_id="a:1",
                to_work_item_id="b:2",
                link_type="semantic_match",
                confidence="high",
                similarity=0.5,
                method="test",
                evidence="x",
            )
        ],
        work_items_capped=0,
    )
    coord = CoordinationLinkInputBundle(evidence=_empty_evidence(bundle), perception_rows=[])
    g = build_execution_graph(bundle, links, coord)
    assert len(g.nodes) == 2
    assert len(g.edges) == 1
    assert g.edges[0].relation == "references"
    assert {g.edges[0].from_id, g.edges[0].to_id} == {"a:1", "b:2"}


def test_low_confidence_link_skipped() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    bundle = WorkItemBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            _wi(id="x:1", source="calls", type="call", title="A"),
            _wi(id="y:2", source="linear", type="issue", title="B"),
        ],
    )
    links = LinkBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        links=[
            WorkItemLink(
                id="l1",
                from_work_item_id="x:1",
                to_work_item_id="y:2",
                link_type="semantic_match",
                confidence="low",
                similarity=0.1,
                method="test",
                evidence="x",
            )
        ],
        work_items_capped=0,
    )
    g = build_execution_graph(
        bundle,
        links,
        CoordinationLinkInputBundle(evidence=_empty_evidence(bundle), perception_rows=[]),
    )
    assert g.edges == []


def test_waits_on_resolved_depends_on() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    bundle = WorkItemBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            _wi(id="call:1", source="calls", type="call", title="Sync"),
            _wi(id="linear:issue:9", source="linear", type="issue", title="NEX-9"),
        ],
    )
    row = PerceptionRow(
        id="p1",
        work_item_id="call:1",
        kind="action_item",
        statement="Waiting on linear:issue:9",
        quote="waiting on linear:issue:9 for signoff",
        waits_on=["linear:issue:9"],
    )
    g = build_execution_graph(
        bundle,
        LinkBundle(run_id=rid, tenant_id=tid, window_days=30, links=[], work_items_capped=0),
        CoordinationLinkInputBundle(evidence=_empty_evidence(bundle), perception_rows=[row]),
    )
    deps = [e for e in g.edges if e.relation == "depends_on"]
    assert len(deps) == 1
    assert deps[0].from_id == "call:1" and deps[0].to_id == "linear:issue:9"
    assert g.unresolved_dependency_refs == []


def test_waits_on_unresolved_recorded_not_edged() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    bundle = WorkItemBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[_wi(id="call:1", source="calls", type="call", title="Sync")],
    )
    row = PerceptionRow(
        id="p1",
        work_item_id="call:1",
        kind="blocker",
        statement="Blocked",
        quote="blocked",
        waits_on=["@legal review team"],
    )
    g = build_execution_graph(
        bundle,
        LinkBundle(run_id=rid, tenant_id=tid, window_days=30, links=[], work_items_capped=0),
        CoordinationLinkInputBundle(evidence=_empty_evidence(bundle), perception_rows=[row]),
    )
    assert g.edges == []
    assert "call:1|waits_on|@legal review team" in g.unresolved_dependency_refs


def test_blocked_by_blocks_edge_direction() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    bundle = WorkItemBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            _wi(id="gh:pr:1", source="github", type="pull_request", title="Fix"),
            _wi(id="linear:issue:1", source="linear", type="issue", title="Bug"),
        ],
    )
    row = PerceptionRow(
        id="p1",
        work_item_id="gh:pr:1",
        kind="blocker",
        statement="Blocked on issue",
        quote="blocked on linear:issue:1",
        blocked_by=["linear:issue:1"],
    )
    g = build_execution_graph(
        bundle,
        LinkBundle(run_id=rid, tenant_id=tid, window_days=30, links=[], work_items_capped=0),
        CoordinationLinkInputBundle(evidence=_empty_evidence(bundle), perception_rows=[row]),
    )
    blk = [e for e in g.edges if e.relation == "blocks"]
    assert len(blk) == 1
    assert blk[0].from_id == "linear:issue:1" and blk[0].to_id == "gh:pr:1"


def test_perception_execution_state_and_owner_on_node() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    bundle = WorkItemBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[_wi(id="wi:1", source="linear", type="issue", title="T", status="open")],
    )
    row = PerceptionRow(
        id="p1",
        work_item_id="wi:1",
        kind="risk",
        statement="Risk",
        quote="risk quote here",
        execution_state="blocked",
        ownership_inferred=PerceptionOwnershipInferred(text_span="@owner", role_guess="IC"),
    )
    g = build_execution_graph(
        bundle,
        LinkBundle(run_id=rid, tenant_id=tid, window_days=30, links=[], work_items_capped=0),
        CoordinationLinkInputBundle(evidence=_empty_evidence(bundle), perception_rows=[row]),
    )
    n = g.nodes[0]
    assert n.execution_state == "blocked"
    assert n.owner_hint == "@owner (IC)"


def test_references_edge_deduped() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    bundle = WorkItemBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            _wi(id="a:1", source="calls", type="call", title="C"),
            _wi(id="b:2", source="linear", type="issue", title="I"),
        ],
    )
    links = LinkBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        links=[
            WorkItemLink(
                id="l1",
                from_work_item_id="a:1",
                to_work_item_id="b:2",
                link_type="semantic_match",
                confidence="high",
                similarity=0.5,
                method="m",
                evidence="e",
            ),
            WorkItemLink(
                id="l2",
                from_work_item_id="b:2",
                to_work_item_id="a:1",
                link_type="semantic_match",
                confidence="medium",
                similarity=0.4,
                method="m",
                evidence="e2",
            ),
        ],
        work_items_capped=0,
    )
    g = build_execution_graph(
        bundle,
        links,
        CoordinationLinkInputBundle(evidence=_empty_evidence(bundle), perception_rows=[]),
    )
    assert len([e for e in g.edges if e.relation == "references"]) == 1
