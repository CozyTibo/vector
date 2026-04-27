"""Tests for Step 5.5 key achievements."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.manager_insights_activity import LinkBundle, WorkItem, WorkItemBundle
from vector.domains.manager_insights.build_key_achievements import build_key_achievements


def _bundle(items: list[WorkItem]) -> WorkItemBundle:
    return WorkItemBundle(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        items=items,
    )


def _empty_links(b: WorkItemBundle) -> LinkBundle:
    return LinkBundle(
        run_id=b.run_id,
        tenant_id=b.tenant_id,
        window_days=b.window_days,
        links=[],
        work_items_capped=0,
    )


def test_includes_closed_issue_and_merged_pr() -> None:
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    b = _bundle(
        [
            WorkItem(
                id="l:1",
                source="linear",
                type="issue",
                title="NEX-1 done",
                status="closed",
                closed_at=t0,
            ),
            WorkItem(
                id="gh:pr:1",
                source="github",
                type="pull_request",
                title="Fix auth",
                status="merged",
                closed_at=t0,
            ),
            WorkItem(
                id="open:1",
                source="linear",
                type="issue",
                title="Still open",
                status="open",
            ),
        ]
    )
    out = build_key_achievements(b, _empty_links(b))
    titles = {x.title for x in out.items}
    assert "NEX-1 done" in titles
    assert "Fix auth" in titles
    assert "Still open" not in titles
    for it in out.items:
        assert it.linked_items
        assert it.evidence


def test_sorts_by_close_time_newest_first() -> None:
    t_old = datetime(2026, 1, 1, tzinfo=UTC)
    t_new = datetime(2026, 2, 1, tzinfo=UTC)
    b = _bundle(
        [
            WorkItem(
                id="a",
                source="linear",
                type="issue",
                title="old",
                status="closed",
                closed_at=t_old,
            ),
            WorkItem(
                id="b",
                source="linear",
                type="issue",
                title="newer",
                status="closed",
                closed_at=t_new,
            ),
        ]
    )
    out = build_key_achievements(b, _empty_links(b))
    assert out.items[0].title == "newer"
    assert out.items[1].title == "old"
