"""§6 Step 27 — prioritize_decisions deterministic ordering."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.manager_insights_activity import (
    DecisionBundle,
    DecisionBundleItem,
    DecisionDefaultAction,
    DecisionItem,
    DecisionRuleTraceDebug,
    SignalsV0Debug,
)
from vector.domains.manager_insights.prioritize_decisions import (
    cap_prioritized_decisions,
    prioritize_decisions,
)


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


def _d(
    *,
    did: str,
    gap_id: str,
    gap_type: str,
    decision_type: str,
    ts: datetime,
    rid: uuid.UUID,
) -> DecisionItem:
    return DecisionItem(
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


def test_prioritize_orders_by_decision_type_then_gap_type_then_id() -> None:
    rid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    tid = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    bundle = DecisionBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            DecisionBundleItem(
                decision=_d(
                    did="coordination:decision:zdoc",
                    gap_id="g-doc",
                    gap_type="doc_not_connected_to_execution",
                    decision_type="DOC_EXECUTION_BRIDGE",
                    ts=ts,
                    rid=rid,
                ),
                decision_debug=None,
            ),
            DecisionBundleItem(
                decision=_d(
                    did="coordination:decision:zhold",
                    gap_id="g-hold",
                    gap_type="discussed_not_linked_to_work",
                    decision_type="HOLD_START",
                    ts=ts,
                    rid=rid,
                ),
                decision_debug=None,
            ),
            DecisionBundleItem(
                decision=_d(
                    did="coordination:decision:zblock",
                    gap_id="g-block",
                    gap_type="blocker_not_tracked",
                    decision_type="BLOCKER_ESCALATION",
                    ts=ts,
                    rid=rid,
                ),
                decision_debug=None,
            ),
        ],
    )
    out = prioritize_decisions(bundle, signals=_sig())
    assert [x.decision.id for x in out] == [
        "coordination:decision:zhold",
        "coordination:decision:zblock",
        "coordination:decision:zdoc",
    ]


def test_prioritize_stable_on_equal_keys() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    ts = datetime(2026, 5, 1, tzinfo=UTC)
    bundle = DecisionBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            DecisionBundleItem(
                decision=_d(
                    did="coordination:decision:aa",
                    gap_id="g2",
                    gap_type="expected_not_executed",
                    decision_type="LINK_OR_CLOSE_COMMITMENT",
                    ts=ts,
                    rid=rid,
                ),
                decision_debug=None,
            ),
            DecisionBundleItem(
                decision=_d(
                    did="coordination:decision:bb",
                    gap_id="g1",
                    gap_type="expected_not_executed",
                    decision_type="LINK_OR_CLOSE_COMMITMENT",
                    ts=ts,
                    rid=rid,
                ),
                decision_debug=None,
            ),
        ],
    )
    out = prioritize_decisions(bundle, signals=_sig())
    assert [x.decision.id for x in out] == ["coordination:decision:aa", "coordination:decision:bb"]


def test_prioritize_with_signals_none() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    ts = datetime(2026, 5, 1, tzinfo=UTC)
    bundle = DecisionBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            DecisionBundleItem(
                decision=_d(
                    did="coordination:decision:zz",
                    gap_id="g2",
                    gap_type="discussed_not_linked_to_work",
                    decision_type="THREAD_TO_TRACKING_LINK",
                    ts=ts,
                    rid=rid,
                ),
                decision_debug=None,
            ),
            DecisionBundleItem(
                decision=_d(
                    did="coordination:decision:aa",
                    gap_id="g1",
                    gap_type="discussed_not_linked_to_work",
                    decision_type="THREAD_TO_TRACKING_LINK",
                    ts=ts,
                    rid=rid,
                ),
                decision_debug=None,
            ),
        ],
    )
    out = prioritize_decisions(bundle, signals=None)
    assert [x.decision.id for x in out] == ["coordination:decision:aa", "coordination:decision:zz"]


def test_cap_prioritized_preserves_debug_fields() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    ts = datetime(2026, 5, 1, tzinfo=UTC)
    dbg = DecisionRuleTraceDebug(
        gap_id="g1",
        matched_rule="test",
        conditions_met={"a": True},
    )
    bundle = DecisionBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            DecisionBundleItem(
                decision=_d(
                    did="coordination:decision:a",
                    gap_id="g1",
                    gap_type="doc_not_connected_to_execution",
                    decision_type="DOC_EXECUTION_BRIDGE",
                    ts=ts,
                    rid=rid,
                ),
                decision_debug=dbg,
            ),
            DecisionBundleItem(
                decision=_d(
                    did="coordination:decision:b",
                    gap_id="g2",
                    gap_type="doc_not_connected_to_execution",
                    decision_type="DOC_EXECUTION_BRIDGE",
                    ts=ts,
                    rid=rid,
                ),
                decision_debug=None,
            ),
        ],
    )
    ordered = prioritize_decisions(bundle, signals=_sig())
    capped, before = cap_prioritized_decisions(ordered, 1)
    assert before == 2
    assert len(capped) == 1
    assert capped[0].decision_debug is not None
    assert capped[0].decision_debug.matched_rule == "test"


def test_prioritize_does_not_mutate_bundle() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    ts = datetime(2026, 5, 1, tzinfo=UTC)
    bundle = DecisionBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            DecisionBundleItem(
                decision=_d(
                    did="coordination:decision:a",
                    gap_id="g1",
                    gap_type="doc_not_connected_to_execution",
                    decision_type="DOC_EXECUTION_BRIDGE",
                    ts=ts,
                    rid=rid,
                ),
                decision_debug=None,
            ),
        ],
    )
    before = [bundle.items[0].decision.id]
    prioritize_decisions(bundle, signals=_sig())
    after = [bundle.items[0].decision.id]
    assert before == after
