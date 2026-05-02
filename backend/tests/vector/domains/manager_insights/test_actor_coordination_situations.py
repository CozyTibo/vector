"""Actor-driven execution situations (Step 6.5) and prioritization (Step 27)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.manager_insights_activity import (
    CoordinationLinkInputBundle,
    DecisionBundle,
    DecisionBundleItem,
    DecisionDefaultAction,
    DecisionItem,
    DecisionRuleTraceDebug,
    EvidenceBundle,
    GapBundle,
    GapItem,
    LinkBundle,
    SignalsV0Debug,
    WorkItem,
    WorkItemBundle,
)
from vector.domains.manager_insights.compute_decisions import SITUATION_TO_FAILURE_MODE, compute_decisions
from vector.domains.manager_insights.detect_execution_situations import detect_execution_situations
from vector.domains.manager_insights.prioritize_decisions import prioritize_decisions


def _signals(**overrides: object) -> SignalsV0Debug:
    base: dict[str, object] = {
        "delivery_strength": "moderate",
        "urgent_pressure": "low",
        "expectation_coverage": "high",
        "follow_through": "strong",
        "blocker_visibility": "visible",
        "repeated_discussion_present": False,
        "execution_momentum": "steady",
        "documentation_linkage": "linked",
        "focus": "focused",
        "collaboration_intensity": "moderate",
        "support_pattern": "balanced",
        "feedback_reception": "neutral",
        "coordination_role": "contributing",
        "interaction_friction": "absent",
        "scope_ambiguity": "low",
        "discussion_churn": "low",
        "contradiction_density": "low",
        "actor_fragmentation": 0,
        "actor_load": 0,
        "actor_consistency": 0.0,
        "explain": {},
    }
    base.update(overrides)
    return SignalsV0Debug.model_validate(base)  # type: ignore[arg-type]


def _gap_bundle() -> GapBundle:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    return GapBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        gaps=[
            GapItem(id="g1", type="discussed_not_linked_to_work", description="d1", evidence_pointers={}),
            GapItem(id="g2", type="expected_not_executed", description="d2", evidence_pointers={}),
        ],
    )


def test_detect_own_fragmentation_situation_uses_signal_threshold() -> None:
    gaps = _gap_bundle()
    sig = _signals(actor_fragmentation=6)
    sits = detect_execution_situations(
        gaps,
        sig,
        perception_rows=[],
        work_items=None,
        links=None,
        evidence=None,
        coordination_input=None,
        hold_start_affected_wi_threshold=2,
        gaps_use_graph=False,
    )
    kinds = {s.type for s in sits}
    assert "OWNERSHIP_FRAGMENTED" in kinds
    frag = next(s for s in sits if s.type == "OWNERSHIP_FRAGMENTED")
    assert frag.actor_situation_metrics is not None
    assert frag.actor_situation_metrics["actor_fragmentation_observed"] == 6
    assert frag.actor_situation_metrics["actor_ids_uuid"] == []


def test_detect_key_person_bottleneck_ratio() -> None:
    gaps = _gap_bundle()
    sig = _signals()
    a = uuid.uuid4()
    run_id = gaps.run_id
    tid = gaps.tenant_id
    items = [
        WorkItem(
            id="linear:o1",
            source="linear",
            type="issue",
            title="A",
            status="open",
            owner_actor_id=a,
            participants=[],
            source_ref={},
        ),
        WorkItem(
            id="linear:o2",
            source="linear",
            type="issue",
            title="B",
            status="open",
            owner_actor_id=a,
            participants=[],
            source_ref={},
        ),
        WorkItem(
            id="linear:o3",
            source="linear",
            type="issue",
            title="C",
            status="open",
            owner_actor_id=a,
            participants=[],
            source_ref={},
        ),
    ]
    bundle = WorkItemBundle(run_id=run_id, tenant_id=tid, window_days=30, items=items)
    sits = detect_execution_situations(
        gaps,
        sig,
        perception_rows=[],
        work_items=bundle,
        links=None,
        evidence=None,
        coordination_input=None,
        hold_start_affected_wi_threshold=2,
        gaps_use_graph=False,
    )
    bottleneck = next((s for s in sits if s.type == "KEY_PERSON_BOTTLENECK"), None)
    assert bottleneck is not None
    m = bottleneck.actor_situation_metrics
    assert m is not None
    assert m["open_execution_total"] == 3
    assert m["max_owner_share_of_open_execution"] > 0.5
    assert str(a) in m["actor_ids_uuid"]


def test_compute_decisions_propagates_actor_situation_metrics_to_debug() -> None:
    gaps = _gap_bundle()
    sig = _signals(actor_fragmentation=7)
    bundle = compute_decisions(gaps, signals=sig, include_decision_debug=True)
    row = next(
        (r for r in bundle.items if r.decision_debug and r.decision_debug.execution_situation == "OWNERSHIP_FRAGMENTED"),
        None,
    )
    assert row is not None
    assert row.decision_debug is not None
    assert row.decision_debug.actor_situation_metrics is not None
    am = row.decision_debug.actor_situation_metrics
    assert am.get("failure_mode_aggregation") is True
    assert any(
        entry.get("metrics", {}).get("rule") == "OWNERSHIP_FRAGMENTED"
        for entry in am.get("by_situation", [])
        if isinstance(entry, dict)
    )
    assert row.decision.required_inputs.get("failure_mode") == "OWNERSHIP_FAILURE"


def test_failure_mode_mapping_covers_specified_situations() -> None:
    assert SITUATION_TO_FAILURE_MODE["OWNERSHIP_FRAGMENTED"] == "OWNERSHIP_FAILURE"
    assert SITUATION_TO_FAILURE_MODE["KEY_PERSON_BOTTLENECK"] == "OWNERSHIP_FAILURE"
    assert SITUATION_TO_FAILURE_MODE["UNKNOWN_OWNERSHIP"] == "OWNERSHIP_FAILURE"
    assert SITUATION_TO_FAILURE_MODE["DECISION_NOT_CONNECTED_TO_OWNER"] == "DECISION_FAILURE"
    assert SITUATION_TO_FAILURE_MODE["DECISION_LOOP"] == "DECISION_FAILURE"
    assert SITUATION_TO_FAILURE_MODE["MISALIGNED_REALITY"] == "EXECUTION_ALIGNMENT_FAILURE"
    assert SITUATION_TO_FAILURE_MODE["SHADOW_WORK"] == "EXECUTION_ALIGNMENT_FAILURE"


def test_prioritize_orders_actor_coordination_before_link_work() -> None:
    rid = uuid.uuid4()
    tid = uuid.uuid4()
    ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)

    def _item(
        *,
        did: str,
        decision_type: str,
        situation: str | None,
    ) -> DecisionBundleItem:
        dbg = (
            DecisionRuleTraceDebug(
                gap_id=did,
                matched_rule=f"execution_situation:{situation}",
                execution_situation=situation,  # type: ignore[arg-type]
                situation_support_count=1,
                actor_situation_metrics={"rule": situation} if situation else None,
            )
            if situation
            else DecisionRuleTraceDebug(
                gap_id=did,
                matched_rule="gap:link_work",
                execution_situation=None,
            )
        )
        return DecisionBundleItem(
            decision=DecisionItem(
                id=did,
                gap_id=did,
                gap_type="aggregated_situation",
                decision_type=decision_type,  # type: ignore[arg-type]
                title="t",
                rationale="r",
                default_action=DecisionDefaultAction(kind="noop"),
                required_inputs={},
                evidence_refs=[],
                signal_refs=[],
                dominant=False,
                created_at=ts,
                run_id=rid,
                status=None,
            ),
            decision_debug=dbg,
        )

    bundle = DecisionBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            _item(did="z-link", decision_type="LINK_WORK", situation=None),
            _item(did="a-frag", decision_type="REDUCE_WIP", situation="OWNERSHIP_FRAGMENTED"),
        ],
    )
    ordered = prioritize_decisions(bundle, signals=None, learning=None)
    assert ordered[0].decision.id == "a-frag"
    assert ordered[1].decision.id == "z-link"
