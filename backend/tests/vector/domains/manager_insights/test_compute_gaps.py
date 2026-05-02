"""Tests for Step 5 deterministic gaps."""

from __future__ import annotations

import uuid

from vector.contracts.manager_insights_activity import (
    CoordinationLinkInputBundle,
    EvidenceBundle,
    EvidenceItem,
    GapType,
    LinkBundle,
    PerceptionRow,
    WorkItem,
    WorkItemBundle,
    WorkItemLink,
)
from vector.domains.manager_insights.compute_gaps import compute_gaps


def _wi(items: list[WorkItem]) -> WorkItemBundle:
    return WorkItemBundle(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        items=items,
    )


def _ev(bundle: WorkItemBundle, *, action_items: list[EvidenceItem], blockers: list[EvidenceItem], decisions: list[EvidenceItem]) -> EvidenceBundle:
    return EvidenceBundle(
        run_id=bundle.run_id,
        tenant_id=bundle.tenant_id,
        window_days=bundle.window_days,
        action_items=action_items,
        blockers=blockers,
        decisions=decisions,
        discarded_without_evidence=0,
    )


def _links(bundle: WorkItemBundle, rows: list[WorkItemLink]) -> LinkBundle:
    return LinkBundle(
        run_id=bundle.run_id,
        tenant_id=bundle.tenant_id,
        window_days=bundle.window_days,
        links=rows,
        work_items_capped=0,
    )


def _coord(
    bundle: WorkItemBundle,
    *,
    action_items: list[EvidenceItem],
    blockers: list[EvidenceItem],
    decisions: list[EvidenceItem],
    perception_rows: list[PerceptionRow] | None = None,
) -> CoordinationLinkInputBundle:
    return CoordinationLinkInputBundle(
        evidence=_ev(bundle, action_items=action_items, blockers=blockers, decisions=decisions),
        perception_rows=list(perception_rows or ()),
    )


def _types(out) -> set[GapType]:
    return {g.type for g in out.gaps}


def test_expected_not_executed_and_discussed_not_linked() -> None:
    w = _wi(
        [
            WorkItem(id="call:1", source="calls", type="call", title="Weekly sync"),
            WorkItem(id="doc:1", source="notion", type="document", title="Plan draft"),
        ]
    )
    a = EvidenceItem(
        id="a1",
        kind="action_item",
        statement="Fix retry logic this week",
        evidence="we should fix retry logic this week",
        source_work_item_id="call:1",
        source_connector="calls",
        source_type="call",
    )
    out = compute_gaps(
        w,
        _links(w, []),
        _coord(w, action_items=[a], blockers=[], decisions=[]),
    )
    ts = _types(out)
    assert "expected_not_executed" in ts
    assert "discussed_not_linked_to_work" in ts


def test_blocker_not_tracked_when_no_issue_or_pr_link() -> None:
    w = _wi([WorkItem(id="call:2", source="calls", type="call", title="Incident review")])
    b = EvidenceItem(
        id="b1",
        kind="blocker",
        statement="Partner API is degraded",
        evidence="we are blocked by partner outage",
        source_work_item_id="call:2",
        source_connector="calls",
        source_type="call",
    )
    out = compute_gaps(
        w,
        _links(w, []),
        _coord(w, action_items=[], blockers=[b], decisions=[]),
    )
    assert "blocker_not_tracked" in _types(out)


def test_doc_not_connected_to_execution_gap() -> None:
    w = _wi([WorkItem(id="doc:2", source="notion", type="document", title="Spec: rollout")])
    out = compute_gaps(
        w,
        _links(w, []),
        _coord(w, action_items=[], blockers=[], decisions=[]),
    )
    assert "doc_not_connected_to_execution" in _types(out)


def test_no_expected_not_executed_when_linked_to_closed_execution() -> None:
    w = _wi(
        [
            WorkItem(id="call:3", source="calls", type="call", title="Standup"),
            WorkItem(
                id="gh:pr:1",
                source="github",
                type="pull_request",
                title="Fix retry logic",
                status="merged",
            ),
        ]
    )
    a = EvidenceItem(
        id="a2",
        kind="action_item",
        statement="Fix retry logic this week",
        evidence="we should fix retry logic this week",
        source_work_item_id="call:3",
        source_connector="calls",
        source_type="call",
    )
    l = WorkItemLink(
        id="l1",
        from_work_item_id="call:3",
        to_work_item_id="gh:pr:1",
        link_type="semantic_match",
        confidence="high",
        similarity=0.8,
        method="test",
        evidence="retry logic overlap",
    )
    out = compute_gaps(
        w,
        _links(w, [l]),
        _coord(w, action_items=[a], blockers=[], decisions=[]),
    )
    assert "expected_not_executed" not in _types(out)


def test_step13_regression_empty_perception_same_gap_types() -> None:
    """§6 Step 13 — empty perception_rows must not change gap detection vs link-only adjacency."""
    w = _wi(
        [
            WorkItem(id="call:1", source="calls", type="call", title="Weekly sync"),
            WorkItem(id="doc:1", source="notion", type="document", title="Plan draft"),
        ]
    )
    a = EvidenceItem(
        id="a1",
        kind="action_item",
        statement="Fix retry logic this week",
        evidence="we should fix retry logic this week",
        source_work_item_id="call:1",
        source_connector="calls",
        source_type="call",
    )
    legacy = compute_gaps(
        w,
        _links(w, []),
        _coord(w, action_items=[a], blockers=[], decisions=[]),
    )
    base = compute_gaps(
        w,
        _links(w, []),
        _coord(w, action_items=[a], blockers=[], decisions=[], perception_rows=[]),
    )
    assert _types(base) == _types(legacy)
    assert len(base.gaps) == len(legacy.gaps)


def test_step13_perception_mention_suppresses_discussed_not_linked() -> None:
    """When a validated PerceptionRow cites another work item id, treat as adjacency for gap checks."""
    w = _wi(
        [
            WorkItem(id="call:disc", source="calls", type="call", title="Design review"),
            WorkItem(
                id="linear:issue:exec-1",
                source="linear",
                type="issue",
                title="Rollout checklist",
                status="open",
            ),
        ]
    )
    d = EvidenceItem(
        id="d1",
        kind="decision",
        statement="Ship when ready",
        evidence="we will ship when linear:issue:exec-1 is green",
        source_work_item_id="call:disc",
        source_connector="calls",
        source_type="call",
    )
    without = compute_gaps(
        w,
        _links(w, []),
        _coord(w, action_items=[], blockers=[], decisions=[d], perception_rows=[]),
    )
    assert "discussed_not_linked_to_work" in _types(without)

    row = PerceptionRow(
        id="p-step13",
        work_item_id="call:disc",
        kind="decision",
        statement="Exec tracked in linear:issue:exec-1.",
        quote="see linear:issue:exec-1 for the checklist",
    )
    with_row = compute_gaps(
        w,
        _links(w, []),
        _coord(w, action_items=[], blockers=[], decisions=[d], perception_rows=[row]),
    )
    assert "discussed_not_linked_to_work" not in _types(with_row)


def test_step18_golden_gaps_use_graph_false_matches_default() -> None:
    """§6 Step 18 — flag off must match omitting the parameter (no gaps_debug, same gaps)."""
    w = _wi(
        [
            WorkItem(id="call:1", source="calls", type="call", title="Weekly sync"),
            WorkItem(id="doc:1", source="notion", type="document", title="Plan draft"),
        ]
    )
    a = EvidenceItem(
        id="a1",
        kind="action_item",
        statement="Fix retry logic this week",
        evidence="we should fix retry logic this week",
        source_work_item_id="call:1",
        source_connector="calls",
        source_type="call",
    )
    c = _coord(w, action_items=[a], blockers=[], decisions=[])
    base = compute_gaps(w, _links(w, []), c)
    explicit = compute_gaps(w, _links(w, []), c, gaps_use_graph=False)
    assert base.model_dump() == explicit.model_dump()
    assert base.gaps_debug is None


def test_step18_gaps_debug_when_gaps_use_graph_enabled() -> None:
    """§6 Step 18 — merged execution-graph adjacency records a one-line QA string."""
    w = _wi(
        [
            WorkItem(id="call:1", source="calls", type="call", title="Weekly sync"),
            WorkItem(id="doc:1", source="notion", type="document", title="Plan draft"),
        ]
    )
    a = EvidenceItem(
        id="a1",
        kind="action_item",
        statement="Fix retry logic this week",
        evidence="we should fix retry logic this week",
        source_work_item_id="call:1",
        source_connector="calls",
        source_type="call",
    )
    out = compute_gaps(
        w,
        _links(w, []),
        _coord(w, action_items=[a], blockers=[], decisions=[]),
        gaps_use_graph=True,
    )
    assert out.gaps_debug is not None
    assert "§6 Step 18" in out.gaps_debug
    assert "graph edges" in out.gaps_debug

