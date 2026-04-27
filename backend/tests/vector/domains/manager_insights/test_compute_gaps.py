"""Tests for Step 5 deterministic gaps."""

from __future__ import annotations

import uuid

from vector.contracts.manager_insights_activity import (
    EvidenceBundle,
    EvidenceItem,
    GapType,
    LinkBundle,
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
        _ev(w, action_items=[a], blockers=[], decisions=[]),
        _links(w, []),
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
        _ev(w, action_items=[], blockers=[b], decisions=[]),
        _links(w, []),
    )
    assert "blocker_not_tracked" in _types(out)


def test_doc_not_connected_to_execution_gap() -> None:
    w = _wi([WorkItem(id="doc:2", source="notion", type="document", title="Spec: rollout")])
    out = compute_gaps(
        w,
        _ev(w, action_items=[], blockers=[], decisions=[]),
        _links(w, []),
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
        _ev(w, action_items=[a], blockers=[], decisions=[]),
        _links(w, [l]),
    )
    assert "expected_not_executed" not in _types(out)

