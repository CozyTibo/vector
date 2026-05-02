"""§6 Step 1 — DecisionItem + DecisionDefaultAction contract tests."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import get_args

import pytest
from pydantic import ValidationError

from vector.domains.manager_insights.perceive_execution_state import build_perception_execution_state_demo_debug
from vector.domains.manager_insights.validate_perception_rows import build_perception_validation_demo_debug
from vector.contracts.manager_insights_activity import (
    CoordinationContractsDebug,
    CoordinationDecisionType,
    DecisionBundle,
    DecisionBundleItem,
    DecisionDefaultAction,
    DecisionItem,
    OutcomeItem,
    PerceptionOwnershipInferred,
    PerceptionRow,
    PerceptionStateTransition,
)


def _minimal_decision_dict() -> dict:
    rid = "550e8400-e29b-41d4-a716-446655440000"
    return {
        "id": "decision:test-1",
        "gap_id": "gap:g1",
        "gap_type": "expected_not_executed",
        "decision_type": "LINK_OR_CLOSE_COMMITMENT",
        "title": "Link or close the commitment",
        "rationale": "One tracked action item has no linked execution artifact.",
        "default_action": {
            "kind": "create_or_link_issue",
            "connector": "linear",
            "payload_template": {"title": "Follow up on action item"},
        },
        "required_inputs": {"assignee_id": None},
        "evidence_refs": ["evidence:action:1"],
        "signal_refs": ["follow_through"],
        "created_at": "2026-01-15T12:00:00+00:00",
        "run_id": rid,
    }


def test_decision_item_model_validate_minimal() -> None:
    d = DecisionItem.model_validate(_minimal_decision_dict())
    assert d.id == "decision:test-1"
    assert d.gap_id == "gap:g1"
    assert d.decision_type == "LINK_OR_CLOSE_COMMITMENT"
    assert d.default_action.kind == "create_or_link_issue"
    assert d.default_action.connector == "linear"


def test_decision_item_round_trip_json() -> None:
    raw = _minimal_decision_dict()
    d1 = DecisionItem.model_validate(raw)
    dumped = d1.model_dump(mode="json")
    d2 = DecisionItem.model_validate(dumped)
    assert d1 == d2
    as_str = json.dumps(dumped)
    d3 = DecisionItem.model_validate(json.loads(as_str))
    assert d1 == d3


def test_decision_item_rejects_unknown_top_level_field() -> None:
    payload = _minimal_decision_dict()
    payload["llm_explanation"] = "nope"
    with pytest.raises(ValidationError) as exc:
        DecisionItem.model_validate(payload)
    assert "llm_explanation" in str(exc.value).lower() or "extra" in str(exc.value).lower()


def test_decision_default_action_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        DecisionDefaultAction.model_validate(
            {
                "kind": "noop",
                "extra_field": 1,
            }
        )


def test_decision_item_invalid_decision_type() -> None:
    payload = _minimal_decision_dict()
    payload["decision_type"] = "NOT_A_REAL_TYPE"
    with pytest.raises(ValidationError):
        DecisionItem.model_validate(payload)


def test_decision_item_empty_gap_id_rejected() -> None:
    payload = _minimal_decision_dict()
    payload["gap_id"] = ""
    with pytest.raises(ValidationError):
        DecisionItem.model_validate(payload)


def test_coordination_contracts_debug_round_trip() -> None:
    run = uuid.UUID("550e8400-e29b-41d4-a716-446655440099")
    tenant = uuid.UUID("550e8400-e29b-41d4-a716-446655440098")
    inner = DecisionItem.model_validate({**_minimal_decision_dict(), "run_id": str(run)})
    bundle = DecisionBundle(
        run_id=run,
        tenant_id=tenant,
        window_days=30,
        items=[DecisionBundleItem(decision=inner, decision_debug=None)],
    )
    outcome = OutcomeItem(
        id=uuid.UUID("660e8400-e29b-41d4-a716-446655440001"),
        decision_id=inner.id,
        tenant_id=tenant,
        observed_at=datetime(2026, 1, 3, tzinfo=UTC),
        outcome_type="ignored",
    )
    perception_row = PerceptionRow(
        id="perception:contract:test",
        work_item_id="wi:test-1",
        kind="ownership_hint",
        statement="Alice owns delivery per thread.",
        quote="Alice will drive the rollout",
        execution_state="in_progress",
        state_transition=PerceptionStateTransition(
            from_state="not_started",
            to_state="in_progress",
            quote="kicking off implementation today",
        ),
        waits_on=[],
        blocked_by=[],
        commitment_strength="strong",
        ambiguity_class=None,
        ownership_inferred=PerceptionOwnershipInferred(text_span="Alice", role_guess="owner"),
    )
    outer = CoordinationContractsDebug(
        decision_item_example=inner,
        decision_bundle_example=bundle,
        outcome_item_example=outcome,
        perception_row_example=perception_row,
        perception_validation_demo=build_perception_validation_demo_debug(),
        perception_execution_state_demo=build_perception_execution_state_demo_debug(),
    )
    dumped = outer.model_dump(mode="json")
    again = CoordinationContractsDebug.model_validate(dumped)
    assert again == outer


def test_decision_item_all_decision_types_accepted() -> None:
    run = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
    ts = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    for i, dt in enumerate(get_args(CoordinationDecisionType)):
        d = DecisionItem(
            id=f"d{i}",
            gap_id=f"g{i}",
            gap_type="blocker_not_tracked",
            decision_type=dt,
            title="t",
            rationale="r",
            default_action=DecisionDefaultAction(kind="noop"),
            created_at=ts,
            run_id=run,
        )
        assert d.decision_type == dt
