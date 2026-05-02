"""§6 Step 39 — admin list API contracts for persisted manager insight outcomes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.admin import ManagerInsightOutcomeRow, ManagerInsightOutcomesListResponse


def test_manager_insight_outcomes_list_response_round_trip() -> None:
    tid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    did = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    oid = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    row = ManagerInsightOutcomeRow(
        id=oid,
        decision_id=did,
        tenant_id=tid,
        observed_at=now,
        outcome_type="applied_success",
        false_positive=False,
        ground_truth={"ok": True},
        user_attribution="qa@example.com",
    )
    payload = ManagerInsightOutcomesListResponse(
        tenant_id=tid,
        total=1,
        limit=50,
        offset=0,
        items=[row],
    )
    dumped = payload.model_dump(mode="json")
    again = ManagerInsightOutcomesListResponse.model_validate(dumped)
    assert again == payload
