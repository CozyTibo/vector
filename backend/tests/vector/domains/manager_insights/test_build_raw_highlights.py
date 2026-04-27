"""Tests for Step 5.6 raw highlights."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.manager_insights_activity import (
    EvidenceBundle,
    GapBundle,
    GapItem,
    LinkBundle,
    WorkItem,
    WorkItemBundle,
)
from vector.domains.manager_insights.build_raw_highlights import build_raw_highlights


def _b(items: list[WorkItem]) -> WorkItemBundle:
    return WorkItemBundle(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        items=items,
    )


def _empty_evid(w: WorkItemBundle) -> EvidenceBundle:
    return EvidenceBundle(
        run_id=w.run_id,
        tenant_id=w.tenant_id,
        window_days=w.window_days,
        action_items=[],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )


def _empty_links(w: WorkItemBundle) -> LinkBundle:
    return LinkBundle(
        run_id=w.run_id,
        tenant_id=w.tenant_id,
        window_days=w.window_days,
        links=[],
        work_items_capped=0,
    )


def test_repeated_token_across_calls() -> None:
    w = _b(
        [
            WorkItem(
                id="c:1",
                source="calls",
                type="call",
                title="billing retry discussion",
            ),
            WorkItem(
                id="c:2",
                source="calls",
                type="call",
                title="billing retry follow up",
            ),
        ]
    )
    g = GapBundle(run_id=w.run_id, tenant_id=w.tenant_id, window_days=w.window_days, gaps=[])
    out = build_raw_highlights(w, _empty_evid(w), _empty_links(w), g)
    assert any("billing" in h.text.lower() and len(h.sources) >= 2 for h in out.items)


def test_gap_rows_have_sources() -> None:
    w = _b([WorkItem(id="x", source="notion", type="document", title="Spec")])
    g = GapBundle(
        run_id=w.run_id,
        tenant_id=w.tenant_id,
        window_days=w.window_days,
        gaps=[
            GapItem(
                id="gap:1",
                type="doc_not_connected_to_execution",
                description="No link to issue",
                evidence_pointers={"document_work_item_ids": ["x"]},
            )
        ],
    )
    out = build_raw_highlights(w, _empty_evid(w), _empty_links(w), g)
    ghl = [h for h in out.items if "doc not connected to execution" in h.text.lower()]
    assert ghl
    assert ghl[0].sources
