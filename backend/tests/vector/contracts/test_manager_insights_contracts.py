"""Step 0 contract tests for Manager Insights canonical DTOs."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from vector.contracts.manager_insights import (
    ActualWork,
    ActionItem,
    DeliveryMetrics,
    Gap,
    InsightArbitrationResult,
    InsightPrimaryEntity,
    InsightV0,
    InterpretationV0,
    Link,
    ReportV0,
    SignalsV0,
    UserReportContext,
    WorkItem,
)
from vector.contracts.manager_insights_activity import (
    ConnectorReliabilityDetail,
    DataReliabilityReport,
)


def _reliability() -> DataReliabilityReport:
    hi = ConnectorReliabilityDetail(tier="high", reasons=["ok"], metrics={"coverage": 1.0})
    return DataReliabilityReport(
        slack=hi,
        github=hi,
        linear=hi,
        notion=hi,
        calls=hi,
        overall_confidence="high",
    )


def test_user_report_context_round_trip_json() -> None:
    ctx = UserReportContext(
        run_id="run_123",
        tenant_id="tenant_1",
        subject_user_id="u_42",
        window_days=30,
        generated_at=datetime.now(tz=UTC),
        data_reliability=_reliability(),
        delivery_metrics=DeliveryMetrics(
            issues_completed=18,
            prs_merged_count=6,
            active_projects=3,
            open_urgent_items=2,
        ),
        work_items=[
            WorkItem(
                id="linear:issue:NEX-1",
                type="issue",
                source="linear",
                title="NEX-1 billing retry under load",
                status="open",
                source_ref={"identifier": "NEX-1"},
            ),
        ],
        links=[
            Link(
                id="link:abc",
                from_work_item_id="call:1",
                to_work_item_id="linear:issue:NEX-1",
                type="semantic_match",
                confidence="medium",
                evidence=["billing retry under load", "same phrase appears in call note"],
                similarity=0.42,
                method="token_jaccard",
            ),
        ],
        action_items=[
            ActionItem(
                id="a1",
                text="Fix retry logic",
                source="call_3",
                evidence="we should fix retry logic this week",
                linked_work_items=["linear:issue:NEX-1"],
                confidence="high",
            )
        ],
        blockers=[],
        decisions=[],
        expected_work=[],
        actual_work=ActualWork(issue_ids=["linear:issue:NEX-1"], pull_request_ids=[]),
        gaps=[
            Gap(
                id="g1",
                type="expected_not_executed",
                description="action item has no linked issue or PR",
                evidence_pointers={"action_item_ids": ["a2"], "linked_items": []},
            )
        ],
        signals=SignalsV0(
            delivery_strength="high",
            urgent_pressure="moderate",
            expectation_coverage="partial",
            follow_through="partial",
            blocker_visibility="partial",
            repeated_discussion_present=True,
            execution_momentum="steady",
            documentation_linkage="partially_linked",
            focus="moderate",
            collaboration_intensity="high",
            support_pattern="balanced",
            feedback_reception="neutral",
            coordination_role="contributing",
            interaction_friction="unclear",
            explain={"follow_through": "2/5 action items linked"},
        ),
        interpretations=[
            InterpretationV0(
                id="i1",
                type="follow_through",
                description="g1 — linear:issue:NEX-1 — Conversion from decisions to tracked execution is partial.",
                based_on_signals=["follow_through"],
                evidence=["2 action items have no tracked issue"],
                confidence="medium",
                based_on_gaps=["g1"],
                based_on_blockers=[],
                based_on_highlights=[],
            )
        ],
        insights=[
            InsightV0(
                id="ins_1",
                observation="g1 — linear:issue:NEX-1 in NEX: fix retry logic (call_3) and no linked issue.",
                interpretation="Follow-through from discussion to execution is inconsistent.",
                implication="Execution reliability may degrade.",
                evidence=["fix retry logic (call_3)", "no linked issue"],
                evidence_ids=["a1"],
                based_on_interpretations=["i1"],
                based_on_signals=["follow_through"],
                primary_work_item_ids=["linear:issue:NEX-1"],
                supporting_work_item_ids=[],
                primary_entities=[InsightPrimaryEntity(name="NEX", kind="project")],
                based_on_gaps=["g1"],
                based_on_blockers=[],
                based_on_highlights=[],
                confidence="high",
                priority="critical",
            )
        ],
        arbitration=InsightArbitrationResult(
            primary_issue_id="ins_1",
            supporting_issue_ids=[],
            dropped_insights=[],
        ),
    )

    dumped = ctx.model_dump(mode="json")
    reloaded = UserReportContext.model_validate(dumped)
    assert reloaded.run_id == "run_123"
    assert reloaded.signals.follow_through == "partial"


def test_contracts_forbid_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        WorkItem(
            id="w1",
            type="issue",
            source="linear",
            title="T",
            unknown_field="nope",  # type: ignore[call-arg]
        )


def test_report_contract_caps_coaching_questions() -> None:
    with pytest.raises(ValidationError):
        ReportV0(
            summary="s",
            key_risks_ranked=[],
            delivery_pulse="d",
            recent_wins=[],
            collaboration_and_ways_of_working=[],
            development_signals=[],
            open_action_items=[],
            coaching_questions=["q1", "q2", "q3", "q4", "q5"],
            one_priority="p",
            final_markdown="m",
        )

