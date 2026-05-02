"""§6 Step 42 — learning demotion in prioritize_decisions (policy/outcome aggregates)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.manager_insights_activity import (
    DecisionBundle,
    DecisionBundleItem,
    DecisionDefaultAction,
    DecisionItem,
    SignalsV0Debug,
)
from vector.domains.manager_insights.decision_sort_learning import DecisionSortLearning
from vector.domains.manager_insights.prioritize_decisions import prioritize_decisions


def _sig(**overrides: object) -> SignalsV0Debug:
    base = dict(
        delivery_strength="moderate",
        urgent_pressure="low",
        expectation_coverage="high",
        follow_through="strong",
        blocker_visibility="visible",
        repeated_discussion_present=False,
        execution_momentum="steady",
        documentation_linkage="linked",
        focus="focused",
        collaboration_intensity="moderate",
        support_pattern="balanced",
        feedback_reception="neutral",
        coordination_role="contributing",
        interaction_friction="absent",
        scope_ambiguity="low",
        discussion_churn="low",
        contradiction_density="low",
        explain={},
    )
    base.update(overrides)
    return SignalsV0Debug.model_validate(base)  # type: ignore[arg-type]


def _item(
    *,
    did: str,
    gap_id: str,
    gap_type: str,
    decision_type: str,
    ts: datetime,
    rid: uuid.UUID,
) -> DecisionBundleItem:
    d = DecisionItem(
        id=did,
        gap_id=gap_id,
        gap_type=gap_type,  # type: ignore[arg-type]
        decision_type=decision_type,  # type: ignore[arg-type]
        title="t",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        created_at=ts,
        run_id=rid,
    )
    return DecisionBundleItem(decision=d, decision_debug=None)


def test_step42_suppress_expected_moves_discussed_earlier() -> None:
    """Heavy demotion on ``expected_not_executed`` inverts gap-type band vs ``discussed_not_linked``."""
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    ts = datetime(2026, 5, 1, tzinfo=UTC)
    bundle = DecisionBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            _item(
                did="coordination:decision:exp",
                gap_id="g-exp",
                gap_type="expected_not_executed",
                decision_type="LINK_OR_CLOSE_COMMITMENT",
                ts=ts,
                rid=rid,
            ),
            _item(
                did="coordination:decision:disc",
                gap_id="g-disc",
                gap_type="discussed_not_linked_to_work",
                decision_type="LINK_OR_CLOSE_COMMITMENT",
                ts=ts,
                rid=rid,
            ),
        ],
    )
    baseline = prioritize_decisions(bundle, signals=_sig(), learning=None)
    assert [x.decision.id for x in baseline] == [
        "coordination:decision:exp",
        "coordination:decision:disc",
    ]

    learning = DecisionSortLearning.from_policy_and_outcome_maps(
        policy_by_gap={"expected_not_executed": (0, True)},
        outcome_fp_by_gap={},
    )
    assert learning.demotion_for_gap_type("expected_not_executed") >= 10_000

    out = prioritize_decisions(bundle, signals=_sig(), learning=learning)
    assert [x.decision.id for x in out] == [
        "coordination:decision:disc",
        "coordination:decision:exp",
    ]


def test_step42_learning_none_matches_prior_step27_order() -> None:
    rid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    tid = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    bundle = DecisionBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            _item(
                did="coordination:decision:zdoc",
                gap_id="g-doc",
                gap_type="doc_not_connected_to_execution",
                decision_type="DOC_EXECUTION_BRIDGE",
                ts=ts,
                rid=rid,
            ),
            _item(
                did="coordination:decision:zhold",
                gap_id="g-hold",
                gap_type="discussed_not_linked_to_work",
                decision_type="HOLD_START",
                ts=ts,
                rid=rid,
            ),
            _item(
                did="coordination:decision:zblock",
                gap_id="g-block",
                gap_type="blocker_not_tracked",
                decision_type="BLOCKER_ESCALATION",
                ts=ts,
                rid=rid,
            ),
        ],
    )
    assert [x.decision.id for x in prioritize_decisions(bundle, signals=_sig(), learning=None)] == [
        "coordination:decision:zhold",
        "coordination:decision:zblock",
        "coordination:decision:zdoc",
    ]
