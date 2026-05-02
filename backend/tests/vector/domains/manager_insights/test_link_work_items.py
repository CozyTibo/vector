"""Tests for Step 4 work-item linking."""

from __future__ import annotations

import uuid

from vector.contracts.manager_insights_activity import (
    CoordinationLinkInputBundle,
    EvidenceBundle,
    EvidenceItem,
    PerceptionRow,
    WorkItem,
    WorkItemBundle,
)
from vector.domains.manager_insights.link_work_items import JACCARD_HIGH, link_work_items


def _b(items: list[WorkItem], *, wid: int = 30) -> WorkItemBundle:
    return WorkItemBundle(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=wid,
        items=items,
    )


def test_billing_retry_titles_produce_at_least_medium_link() -> None:
    a = WorkItem(
        id="c:1",
        source="calls",
        type="call",
        title="Billing call — billing retry fails under load in checkout",
    )
    b = WorkItem(
        id="l:1",
        source="linear",
        type="issue",
        title="NEX-99: billing retry fails under load in checkout (customer impact)",
    )
    out = link_work_items(_b([a, b]))
    assert len(out.links) == 1
    lk = out.links[0]
    assert lk.from_work_item_id == "c:1"
    assert lk.to_work_item_id == "l:1"
    assert lk.from_work_item_id < lk.to_work_item_id
    assert lk.confidence in ("high", "medium", "low")
    assert "billing" in lk.evidence


def test_shared_ticket_key_uses_shared_reference() -> None:
    a = WorkItem(
        id="g:1",
        source="github",
        type="issue",
        title="[NEX-1] track billing retry in api",
    )
    b = WorkItem(
        id="li:1",
        source="linear",
        type="issue",
        title="NEX-1 — follow up: billing retry hotfix for pilot",
    )
    out = link_work_items(_b([a, b]))
    assert len(out.links) == 1
    assert out.links[0].link_type == "shared_reference"
    assert "NEX-1" in out.links[0].evidence


def test_unrelated_titles_produce_no_links() -> None:
    a = WorkItem(id="a", source="notion", type="document", title="qzx unrelated alpha")
    b = WorkItem(id="b", source="slack", type="message_thread", title="mnp beta gamma")
    out = link_work_items(_b([a, b]))
    assert not out.links


def test_high_confidence_respects_scoring() -> None:
    a = WorkItem(
        id="a",
        source="github",
        type="pull_request",
        title="Implement rollout for NEX-49 and related billing work",
    )
    b = WorkItem(
        id="b",
        source="linear",
        type="issue",
        title="NEX-49: Implement rollout and billing work for the pilot",
    )
    out = link_work_items(_b([a, b]))
    assert out.links
    for row in out.links:
        if row.confidence == "high":
            assert (
                row.similarity + 1e-6 >= JACCARD_HIGH
                or row.link_type == "shared_reference"
            )


def test_step3_snippet_hits_extra_tokens_on_other_work_item() -> None:
    """When Step-3 text mentions tokens from the *other* item, a small nudge is applied (see _evidence_cross_hit_boost)."""
    a = WorkItem(
        id="a1",
        source="linear",
        type="issue",
        title="Retry loop in billing",
    )
    b = WorkItem(
        id="b1",
        source="notion",
        type="document",
        title="Meeting: reliability pilot notes",
    )
    bundle = _b([a, b])
    ev = EvidenceBundle(
        run_id=bundle.run_id,
        tenant_id=bundle.tenant_id,
        window_days=bundle.window_days,
        action_items=[
            EvidenceItem(
                id="e1",
                kind="action_item",
                statement="pilot and reliability are blocked until we ship the fix",
                evidence="pilot and reliability for meeting notes on monday",
                source_work_item_id="a1",
                source_connector="linear",
                source_type="issue",
            )
        ],
        blockers=[],
        decisions=[],
    )
    with_ev = link_work_items(
        bundle,
        link_input=CoordinationLinkInputBundle(evidence=ev, perception_rows=[]),
    )
    assert with_ev.links
    assert any("cross_item_text_hits" in L.method for L in with_ev.links)
    assert with_ev.perception_rows_used_for_linking == 0


def test_step12_perception_rows_merge_for_cross_item_text_hits() -> None:
    """Validated PerceptionRow text feeds the same cross-item boost surface as Step-3 evidence."""
    a = WorkItem(
        id="a1",
        source="linear",
        type="issue",
        title="Retry loop in billing",
    )
    b = WorkItem(
        id="b1",
        source="notion",
        type="document",
        title="Meeting: reliability pilot notes",
    )
    bundle = _b([a, b])
    ev = EvidenceBundle(
        run_id=bundle.run_id,
        tenant_id=bundle.tenant_id,
        window_days=bundle.window_days,
        action_items=[],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )
    rows = [
        PerceptionRow(
            id="p1",
            work_item_id="a1",
            kind="action_item",
            statement="pilot and reliability are blocked until we ship the fix",
            quote="pilot and reliability for meeting notes on monday",
        )
    ]
    out = link_work_items(bundle, link_input=CoordinationLinkInputBundle(evidence=ev, perception_rows=rows))
    assert out.links
    assert any("cross_item_text_hits" in L.method for L in out.links)
    assert any("perception_rows" in L.method for L in out.links)
    assert out.perception_rows_used_for_linking == 1
