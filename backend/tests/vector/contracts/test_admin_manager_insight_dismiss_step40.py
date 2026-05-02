"""§6 Step 40 — admin dismiss API contracts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.admin import (
    ManagerInsightDismissDecisionRequest,
    ManagerInsightDismissDecisionResponse,
    ManagerInsightOutcomeRow,
)


def test_manager_insight_dismiss_request_round_trip() -> None:
    req = ManagerInsightDismissDecisionRequest(
        user_attribution="admin@example.com",
        false_positive=False,
        ground_truth={"source": "admin"},
    )
    dumped = req.model_dump(mode="json")
    again = ManagerInsightDismissDecisionRequest.model_validate(dumped)
    assert again == req


def test_manager_insight_dismiss_response_round_trip() -> None:
    tid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    did = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    oid = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    now = datetime(2026, 5, 4, 12, 0, 0, tzinfo=UTC)
    outcome = ManagerInsightOutcomeRow(
        id=oid,
        decision_id=did,
        tenant_id=tid,
        observed_at=now,
        outcome_type="dismissed",
        false_positive=None,
        ground_truth={},
        user_attribution=None,
    )
    payload = ManagerInsightDismissDecisionResponse(
        tenant_id=tid,
        decision_id=did,
        decision_status="dismissed",
        idempotent=False,
        outcome=outcome,
    )
    dumped = payload.model_dump(mode="json")
    again = ManagerInsightDismissDecisionResponse.model_validate(dumped)
    assert again == payload
