"""§6 Step 33 — admin list API contracts for persisted manager insight decisions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.contracts.admin import ManagerInsightDecisionRow, ManagerInsightDecisionsListResponse


def test_manager_insight_decisions_list_response_round_trip() -> None:
    tid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    rid = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    pk = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    row = ManagerInsightDecisionRow(
        id=pk,
        tenant_id=tid,
        run_id=rid,
        gap_id="g1",
        gap_type="blocker_not_tracked",
        decision_type="BLOCKER_ESCALATION",
        title="Escalate",
        rationale="r",
        default_action={"kind": "noop"},
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        status="proposed",
        rank=1,
        slack_channel_id=None,
        slack_message_ts=None,
        idempotency_key=None,
        receipt=None,
        created_at=now,
        updated_at=now,
    )
    payload = ManagerInsightDecisionsListResponse(
        tenant_id=tid,
        total=1,
        limit=50,
        offset=0,
        items=[row],
    )
    dumped = payload.model_dump(mode="json")
    again = ManagerInsightDecisionsListResponse.model_validate(dumped)
    assert again == payload
