"""§6 Step 41 — admin evaluate-outcomes contracts."""

from __future__ import annotations

import uuid

from vector.contracts.admin import (
    ManagerInsightEvaluateOutcomeItemResult,
    ManagerInsightEvaluateOutcomesRequest,
    ManagerInsightEvaluateOutcomesResponse,
)


def test_evaluate_outcomes_request_round_trip() -> None:
    req = ManagerInsightEvaluateOutcomesRequest(limit=10, reset=True)
    dumped = req.model_dump(mode="json")
    again = ManagerInsightEvaluateOutcomesRequest.model_validate(dumped)
    assert again == req


def test_evaluate_outcomes_response_round_trip() -> None:
    tid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    oid = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    did = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    item = ManagerInsightEvaluateOutcomeItemResult(
        outcome_id=oid,
        decision_id=did,
        rules_applied=["stamp"],
        ground_truth_before={},
        ground_truth_after={"rule_version": "step41_v0", "evaluated_at": "2026-05-05T12:00:00Z"},
    )
    payload = ManagerInsightEvaluateOutcomesResponse(
        tenant_id=tid,
        processed=1,
        skipped=0,
        scanned=1,
        items=[item],
    )
    dumped = payload.model_dump(mode="json")
    again = ManagerInsightEvaluateOutcomesResponse.model_validate(dumped)
    assert again.processed == 1
    assert len(again.items) == 1
