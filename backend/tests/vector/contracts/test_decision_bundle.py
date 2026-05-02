"""§6 Step 2 — DecisionBundle, OutcomeItem, enums, decision_debug contract tests."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import get_args

import pytest
from pydantic import ValidationError

from vector.contracts.manager_insights_activity import (
    DecisionBundle,
    DecisionBundleItem,
    DecisionEmissionTraceDebug,
    DecisionItem,
    DecisionLifecycleStatus,
    DecisionRuleTraceDebug,
    OutcomeItem,
    OutcomeType,
)


def _decision_min(**overrides: object) -> dict:
    base = {
        "id": "d1",
        "gap_id": "g1",
        "gap_type": "expected_not_executed",
        "decision_type": "LINK_OR_CLOSE_COMMITMENT",
        "title": "t",
        "rationale": "r",
        "default_action": {"kind": "k"},
        "required_inputs": {},
        "evidence_refs": [],
        "signal_refs": [],
        "created_at": "2026-01-01T00:00:00+00:00",
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
    }
    return {**base, **overrides}


def test_decision_bundle_round_trip_with_emission_debug() -> None:
    rid = uuid.UUID("550e8400-e29b-41d4-a716-446655440020")
    tid = uuid.UUID("550e8400-e29b-41d4-a716-446655440021")
    d = DecisionItem.model_validate(_decision_min(decision_type="HOLD_START"))
    em = DecisionEmissionTraceDebug(
        evaluated=True,
        inputs_complete=True,
        ambiguity_signal_high=True,
        cluster_hops_used=3,
        seed_work_item_ids=["a"],
        cluster_work_item_ids=["a", "b"],
        open_execution_work_item_ids=["b"],
        open_execution_count=1,
        affected_wi_threshold=0,
        decision_evidence_ids_in_cluster=[],
        guard_ambiguity_ok=True,
        guard_no_decision_evidence_in_cluster_ok=True,
        guard_open_execution_count_ok=True,
        hold_start_emitted=True,
        reason="test",
    )
    bundle = DecisionBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[DecisionBundleItem(decision=d, decision_debug=None, decision_emission_debug=em)],
    )
    dumped = bundle.model_dump(mode="json")
    assert DecisionBundle.model_validate(dumped) == bundle


def test_decision_bundle_round_trip_json() -> None:
    rid = uuid.UUID("550e8400-e29b-41d4-a716-446655440010")
    tid = uuid.UUID("550e8400-e29b-41d4-a716-446655440011")
    d = DecisionItem.model_validate(_decision_min())
    bundle = DecisionBundle(
        run_id=rid,
        tenant_id=tid,
        window_days=30,
        items=[
            DecisionBundleItem(
                decision=d,
                decision_debug=DecisionRuleTraceDebug(
                    gap_id="g1",
                    matched_rule="rule-a",
                    conditions_met={"x": True},
                ),
            ),
        ],
    )
    dumped = bundle.model_dump(mode="json")
    again = DecisionBundle.model_validate(dumped)
    assert again == bundle
    as_json = json.dumps(dumped)
    assert DecisionBundle.model_validate(json.loads(as_json)) == bundle


def test_decision_bundle_rejects_unknown_field() -> None:
    rid = uuid.UUID("550e8400-e29b-41d4-a716-446655440012")
    tid = uuid.UUID("550e8400-e29b-41d4-a716-446655440013")
    payload = {
        "run_id": str(rid),
        "tenant_id": str(tid),
        "window_days": 30,
        "items": [],
        "spurious": 1,
    }
    with pytest.raises(ValidationError):
        DecisionBundle.model_validate(payload)


def test_decision_rule_trace_rejects_unknown() -> None:
    with pytest.raises(ValidationError):
        DecisionRuleTraceDebug.model_validate(
            {"gap_id": "g", "matched_rule": "r", "extra": True},
        )


def test_outcome_item_round_trip_and_enums() -> None:
    oid = uuid.UUID("770e8400-e29b-41d4-a716-446655440014")
    tid = uuid.UUID("550e8400-e29b-41d4-a716-446655440015")
    for ot in get_args(OutcomeType):
        o = OutcomeItem(
            id=oid,
            decision_id="dec-1",
            tenant_id=tid,
            observed_at=datetime(2026, 2, 1, tzinfo=UTC),
            outcome_type=ot,
            ground_truth={"ok": True},
        )
        dumped = o.model_dump(mode="json")
        assert OutcomeItem.model_validate(dumped).outcome_type == ot


def test_outcome_item_rejects_unknown() -> None:
    with pytest.raises(ValidationError):
        OutcomeItem.model_validate(
            {
                "id": "770e8400-e29b-41d4-a716-446655440014",
                "decision_id": "d",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440015",
                "observed_at": "2026-02-01T00:00:00+00:00",
                "outcome_type": "dismissed",
                "nope": 1,
            },
        )


def test_decision_lifecycle_status_literal_coverage() -> None:
    d = DecisionItem.model_validate(
        _decision_min(status="proposed"),
    )
    assert d.status == "proposed"
    for s in get_args(DecisionLifecycleStatus):
        x = DecisionItem.model_validate(_decision_min(status=s))
        assert x.status == s


def test_decision_bundle_item_without_debug() -> None:
    d = DecisionItem.model_validate(_decision_min())
    row = DecisionBundleItem(decision=d, decision_debug=None)
    assert row.decision_debug is None
    dumped = row.model_dump(mode="json")
    assert DecisionBundleItem.model_validate(dumped) == row
