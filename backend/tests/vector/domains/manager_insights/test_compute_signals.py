"""Tests for Step 6 deterministic signal computation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from vector.contracts.manager_insights_activity import (
    CoordinationLinkInputBundle,
    EvidenceBundle,
    EvidenceItem,
    GapBundle,
    GapItem,
    KeyAchievementsBundleDebug,
    LinkBundle,
    PerceptionRow,
    RawHighlightItem,
    RawHighlightsBundleDebug,
    WorkItem,
    WorkItemBundle,
    WorkItemLink,
)
from vector.domains.manager_insights.compute_signals import compute_signals


def _wi(
    wid: str,
    *,
    source: str,
    item_type: str,
    title: str,
    summary: str | None = None,
    status: str | None = None,
    project: str | None = None,
    owner: str | None = None,
    participants: list[str] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    closed_at: datetime | None = None,
) -> WorkItem:
    return WorkItem(
        id=wid,
        source=source,  # type: ignore[arg-type]
        type=item_type,  # type: ignore[arg-type]
        title=title,
        summary=summary,
        status=status,
        project=project,
        owner=owner,
        participants=participants or [],
        created_at=created_at,
        updated_at=updated_at,
        closed_at=closed_at,
        source_ref={},
    )


def test_compute_signals_balanced_dataset_produces_expected_vector() -> None:
    now = datetime(2026, 4, 27, 12, 0, 0, tzinfo=UTC)
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    work_items = WorkItemBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        items=[
            _wi(
                "calls:c1",
                source="calls",
                item_type="call",
                title="Incident sync",
                summary="Need help, blocked on rollout clarification",
                owner="mgr@nexora.dev",
                participants=["a@nexora.dev", "b@nexora.dev"],
                created_at=now - timedelta(days=20),
            ),
            _wi(
                "calls:c2",
                source="calls",
                item_type="call",
                title="Delivery review",
                summary="Can someone help close NEX-2",
                owner="pm@nexora.dev",
                participants=["a@nexora.dev", "c@nexora.dev"],
                created_at=now - timedelta(days=12),
            ),
            _wi(
                "slack:s1",
                source="slack",
                item_type="message_thread",
                title="Slack thread in #eng-core",
                summary="Need help with incident context",
                owner="lead@nexora.dev",
                participants=["d@nexora.dev"],
                created_at=now - timedelta(days=8),
            ),
            _wi(
                "linear:i1",
                source="linear",
                item_type="issue",
                title="NEX-1 urgent API incident",
                status="done",
                project="api",
                updated_at=now - timedelta(days=10),
                closed_at=now - timedelta(days=9),
            ),
            _wi(
                "linear:i2",
                source="linear",
                item_type="issue",
                title="NEX-2 web auth fix",
                status="closed",
                project="web",
                updated_at=now - timedelta(days=7),
                closed_at=now - timedelta(days=6),
            ),
            _wi(
                "github:pr:1",
                source="github",
                item_type="pull_request",
                title="Merge NEX-1 fix",
                status="merged",
                project="api",
                updated_at=now - timedelta(days=5),
                closed_at=now - timedelta(days=5),
            ),
            _wi(
                "github:pr:2",
                source="github",
                item_type="pull_request",
                title="Merge NEX-2 follow-up",
                status="closed",
                project="mobile",
                updated_at=now - timedelta(days=3),
                closed_at=now - timedelta(days=3),
            ),
            _wi(
                "linear:open1",
                source="linear",
                item_type="issue",
                title="Urgent P1 outage in integrations",
                status="open",
                project="integrations",
            ),
            _wi(
                "linear:open2",
                source="linear",
                item_type="issue",
                title="Critical incident in data pipeline",
                status="in_progress",
                project="data",
            ),
            _wi(
                "linear:open3",
                source="linear",
                item_type="issue",
                title="P0 payment blocker",
                status="open",
                project="payments",
            ),
            _wi(
                "notion:d1",
                source="notion",
                item_type="document",
                title="Spec NEX-1",
                status="active",
            ),
            _wi(
                "notion:d2",
                source="notion",
                item_type="document",
                title="Spec NEX-99",
                status="active",
            ),
        ],
    )

    evidence = EvidenceBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        action_items=[
            EvidenceItem(
                id="a1",
                kind="action_item",
                statement="Need help closing NEX-1",
                evidence="Need help closing NEX-1",
                source_work_item_id="calls:c1",
                source_connector="calls",
                source_type="call",
                source_ref={},
                linked_work_items=[],
            ),
            EvidenceItem(
                id="a2",
                kind="action_item",
                statement="Can someone ship NEX-2",
                evidence="Can someone ship NEX-2",
                source_work_item_id="calls:c2",
                source_connector="calls",
                source_type="call",
                source_ref={},
                linked_work_items=[],
            ),
            EvidenceItem(
                id="a3",
                kind="action_item",
                statement="Need help with incident context",
                evidence="Need help with incident context",
                source_work_item_id="slack:s1",
                source_connector="slack",
                source_type="message_thread",
                source_ref={},
                linked_work_items=[],
            ),
            EvidenceItem(
                id="a4",
                kind="action_item",
                statement="Need help and clarification on owner",
                evidence="Need help and clarification on owner",
                source_work_item_id="calls:c1",
                source_connector="calls",
                source_type="call",
                source_ref={},
                linked_work_items=[],
            ),
        ],
        blockers=[
            EvidenceItem(
                id="b1",
                kind="blocker",
                statement="Blocked on partner response",
                evidence="Blocked on partner response",
                source_work_item_id="calls:c1",
                source_connector="calls",
                source_type="call",
                source_ref={},
                linked_work_items=[],
            ),
            EvidenceItem(
                id="b2",
                kind="blocker",
                statement="Stuck waiting on review",
                evidence="Stuck waiting on review",
                source_work_item_id="slack:s1",
                source_connector="slack",
                source_type="message_thread",
                source_ref={},
                linked_work_items=[],
            ),
        ],
        decisions=[
            EvidenceItem(
                id="d1",
                kind="decision",
                statement="Decided to phase rollout by region",
                evidence="Decided to phase rollout by region",
                source_work_item_id="calls:c1",
                source_connector="calls",
                source_type="call",
                source_ref={},
                linked_work_items=[],
            ),
            EvidenceItem(
                id="d2",
                kind="decision",
                statement="We will keep incident follow-up weekly",
                evidence="We will keep incident follow-up weekly",
                source_work_item_id="calls:c2",
                source_connector="calls",
                source_type="call",
                source_ref={},
                linked_work_items=[],
            ),
        ],
        discarded_without_evidence=0,
    )

    links = LinkBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        links=[
            WorkItemLink(
                id="l1",
                from_work_item_id="calls:c1",
                to_work_item_id="linear:i1",
                link_type="semantic_match",
                confidence="high",
                similarity=0.8,
                method="token_jaccard",
                evidence="same issue id",
            ),
            WorkItemLink(
                id="l2",
                from_work_item_id="calls:c2",
                to_work_item_id="github:pr:1",
                link_type="semantic_match",
                confidence="medium",
                similarity=0.5,
                method="token_jaccard",
                evidence="same topic",
            ),
            WorkItemLink(
                id="l3",
                from_work_item_id="slack:s1",
                to_work_item_id="linear:i2",
                link_type="semantic_match",
                confidence="medium",
                similarity=0.45,
                method="token_jaccard",
                evidence="same topic",
            ),
            WorkItemLink(
                id="l4",
                from_work_item_id="notion:d1",
                to_work_item_id="linear:i1",
                link_type="semantic_match",
                confidence="high",
                similarity=0.65,
                method="token_jaccard",
                evidence="same issue id",
            ),
        ],
        work_items_capped=0,
    )

    gaps = GapBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        gaps=[
            GapItem(id="g1", type="expected_not_executed", description="1 action not executed", evidence_pointers={}),
            GapItem(id="g2", type="blocker_not_tracked", description="1 blocker untracked", evidence_pointers={}),
            GapItem(
                id="g3",
                type="discussed_not_linked_to_work",
                description="discussion not linked",
                evidence_pointers={},
            ),
            GapItem(id="g4", type="doc_not_connected_to_execution", description="doc not linked", evidence_pointers={}),
        ],
    )

    signals = compute_signals(
        work_items=work_items,
        links=links,
        gaps=gaps,
        key_achievements=KeyAchievementsBundleDebug(
            run_id=run_id, tenant_id=tenant_id, window_days=30, items=[]
        ),
        raw_highlights=RawHighlightsBundleDebug(
            run_id=run_id,
            tenant_id=tenant_id,
            window_days=30,
            items=[RawHighlightItem(id="rh1", text='Term "incident" appears in 3 distinct calls/Slack work items.', sources=["calls:c1", "calls:c2", "slack:s1"])],
        ),
        coordination_input=CoordinationLinkInputBundle(evidence=evidence, perception_rows=[]),
    )

    assert signals.delivery_strength == "moderate"
    assert signals.urgent_pressure == "high"
    assert signals.expectation_coverage == "partial"
    assert signals.follow_through == "strong"
    assert signals.blocker_visibility == "partial"
    assert signals.repeated_discussion_present is True
    assert signals.documentation_linkage == "partially_linked"
    assert signals.focus == "fragmented"
    assert signals.support_pattern == "asks_for_help"
    assert signals.feedback_reception == "neutral"
    assert signals.coordination_role == "driving"
    assert signals.interaction_friction == "present"
    assert signals.discussion_churn == "moderate"  # §6 Step 20: discussed_not_linked gap + repeated-term highlight
    assert len(signals.explain.keys()) == 20
    assert "§6 Step 20" in signals.explain["scope_ambiguity"]
    assert "§6 Step 20" in signals.explain["discussion_churn"]
    assert "§6 Step 20" in signals.explain["contradiction_density"]
    assert "action coverage=" in signals.explain["expectation_coverage"]


def test_compute_signals_sparse_inputs_default_to_neutral_sentinels() -> None:
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    work_items = WorkItemBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        items=[
            _wi("notion:d1", source="notion", item_type="document", title="Unlinked doc"),
        ],
    )
    evidence = EvidenceBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        action_items=[],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )
    links = LinkBundle(run_id=run_id, tenant_id=tenant_id, window_days=30, links=[], work_items_capped=0)
    gaps = GapBundle(run_id=run_id, tenant_id=tenant_id, window_days=30, gaps=[])
    highlights = RawHighlightsBundleDebug(run_id=run_id, tenant_id=tenant_id, window_days=30, items=[])
    achievements = KeyAchievementsBundleDebug(run_id=run_id, tenant_id=tenant_id, window_days=30, items=[])

    coord = CoordinationLinkInputBundle(evidence=evidence, perception_rows=[])
    signals = compute_signals(
        work_items,
        links,
        gaps,
        achievements,
        highlights,
        coordination_input=coord,
    )
    assert signals.delivery_strength == "low"
    assert signals.urgent_pressure == "low"
    assert signals.expectation_coverage == "partial"
    assert signals.follow_through == "partial"
    assert signals.blocker_visibility == "partial"
    assert signals.repeated_discussion_present is False
    assert signals.feedback_reception == "neutral"
    assert signals.interaction_friction == "absent"


def test_step14_regression_omitted_vs_empty_perception_list() -> None:
    """§6 Step 14 — explicit empty perception_rows matches default empty list."""
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    work_items = WorkItemBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        items=[
            _wi("notion:d1", source="notion", item_type="document", title="Unlinked doc"),
        ],
    )
    evidence = EvidenceBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        action_items=[],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )
    links = LinkBundle(run_id=run_id, tenant_id=tenant_id, window_days=30, links=[], work_items_capped=0)
    gaps = GapBundle(run_id=run_id, tenant_id=tenant_id, window_days=30, gaps=[])
    highlights = RawHighlightsBundleDebug(run_id=run_id, tenant_id=tenant_id, window_days=30, items=[])
    achievements = KeyAchievementsBundleDebug(run_id=run_id, tenant_id=tenant_id, window_days=30, items=[])
    a = compute_signals(
        work_items,
        links,
        gaps,
        achievements,
        highlights,
        coordination_input=CoordinationLinkInputBundle(evidence=evidence),
    )
    b = compute_signals(
        work_items,
        links,
        gaps,
        achievements,
        highlights,
        coordination_input=CoordinationLinkInputBundle(evidence=evidence, perception_rows=[]),
    )
    assert a.model_dump() == b.model_dump()


def test_step14_perception_text_increases_friction_markers() -> None:
    """Validated perception prose is merged into term-based friction (architecture lock)."""
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    work_items = WorkItemBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        items=[
            _wi("notion:d1", source="notion", item_type="document", title="Unlinked doc"),
        ],
    )
    evidence = EvidenceBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        action_items=[],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )
    links = LinkBundle(run_id=run_id, tenant_id=tenant_id, window_days=30, links=[], work_items_capped=0)
    gaps = GapBundle(run_id=run_id, tenant_id=tenant_id, window_days=30, gaps=[])
    highlights = RawHighlightsBundleDebug(run_id=run_id, tenant_id=tenant_id, window_days=30, items=[])
    achievements = KeyAchievementsBundleDebug(run_id=run_id, tenant_id=tenant_id, window_days=30, items=[])
    base = compute_signals(
        work_items,
        links,
        gaps,
        achievements,
        highlights,
        coordination_input=CoordinationLinkInputBundle(evidence=evidence, perception_rows=[]),
    )
    assert base.interaction_friction == "absent"
    row = PerceptionRow(
        id="p-step14",
        work_item_id="notion:d1",
        kind="risk",
        statement="blocked waiting on clarification confusion unclear disagree",
        quote="blocked waiting on clarification confusion unclear disagree",
    )
    with_perception = compute_signals(
        work_items,
        links,
        gaps,
        achievements,
        highlights,
        coordination_input=CoordinationLinkInputBundle(evidence=evidence, perception_rows=[row]),
    )
    assert with_perception.interaction_friction == "present"


def _minimal_signals_inputs(
    *,
    perception_rows: list[PerceptionRow],
    gaps: list[GapItem],
    raw_items: list[RawHighlightItem] | None = None,
) -> tuple[WorkItemBundle, LinkBundle, GapBundle, KeyAchievementsBundleDebug, RawHighlightsBundleDebug, CoordinationLinkInputBundle]:
    """Tiny bundle for §6 Step 20 signal predicate tests."""
    run_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    work_items = WorkItemBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        items=[_wi("linear:x1", source="linear", item_type="issue", title="Scope creep and unclear scope on boundary", summary="")],
    )
    evidence = EvidenceBundle(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        action_items=[],
        blockers=[],
        decisions=[],
        discarded_without_evidence=0,
    )
    links = LinkBundle(run_id=run_id, tenant_id=tenant_id, window_days=30, links=[], work_items_capped=0)
    gap_bundle = GapBundle(run_id=run_id, tenant_id=tenant_id, window_days=30, gaps=gaps)
    highlights = RawHighlightsBundleDebug(
        run_id=run_id,
        tenant_id=tenant_id,
        window_days=30,
        items=raw_items or [],
    )
    achievements = KeyAchievementsBundleDebug(run_id=run_id, tenant_id=tenant_id, window_days=30, items=[])
    coord = CoordinationLinkInputBundle(evidence=evidence, perception_rows=perception_rows)
    return work_items, links, gap_bundle, achievements, highlights, coord


def test_step20_scope_ambiguity_high_from_two_unclear_scope_rows() -> None:
    rows = [
        PerceptionRow(
            id="p1",
            work_item_id="linear:x1",
            kind="ambiguity",
            statement="Scope is unclear",
            quote="Scope is unclear",
            ambiguity_class="unclear_scope",
        ),
        PerceptionRow(
            id="p2",
            work_item_id="linear:x1",
            kind="ambiguity",
            statement="Still unclear scope",
            quote="Still unclear scope",
            ambiguity_class="unclear_scope",
        ),
    ]
    wi, li, gb, ach, hi, coord = _minimal_signals_inputs(perception_rows=rows, gaps=[])
    s = compute_signals(wi, li, gb, ach, hi, coordination_input=coord)
    assert s.scope_ambiguity == "high"
    assert "unclear_scope perception rows=2" in s.explain["scope_ambiguity"]


def test_step20_discussion_churn_high_from_two_discussion_loop_rows() -> None:
    rows = [
        PerceptionRow(
            id="p1",
            work_item_id="linear:x1",
            kind="ambiguity",
            statement="Thread keeps reopening",
            quote="Thread keeps reopening",
            ambiguity_class="discussion_loop",
        ),
        PerceptionRow(
            id="p2",
            work_item_id="linear:x1",
            kind="ambiguity",
            statement="Circling again",
            quote="Circling again",
            ambiguity_class="discussion_loop",
        ),
    ]
    wi, li, gb, ach, hi, coord = _minimal_signals_inputs(perception_rows=rows, gaps=[])
    s = compute_signals(wi, li, gb, ach, hi, coordination_input=coord)
    assert s.discussion_churn == "high"
    assert "discussion_loop rows=2" in s.explain["discussion_churn"]


def test_step20_contradiction_density_high_from_two_contradiction_rows() -> None:
    rows = [
        PerceptionRow(
            id="p1",
            work_item_id="linear:x1",
            kind="ambiguity",
            statement="Says A",
            quote="Says A",
            ambiguity_class="contradiction",
            ambiguity_quote="Says A",
            contradiction_pair_id="pair-1",
        ),
        PerceptionRow(
            id="p2",
            work_item_id="linear:x1",
            kind="ambiguity",
            statement="Says B",
            quote="Says B",
            ambiguity_class="contradiction",
            ambiguity_quote="Says B",
            contradiction_pair_id="pair-1",
        ),
    ]
    wi, li, gb, ach, hi, coord = _minimal_signals_inputs(perception_rows=rows, gaps=[])
    s = compute_signals(wi, li, gb, ach, hi, coordination_input=coord)
    assert s.contradiction_density == "high"
    assert "contradiction perception rows=2" in s.explain["contradiction_density"]
