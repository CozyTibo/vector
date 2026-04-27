"""Tests for Step 3 evidence extraction."""

from __future__ import annotations

import uuid

from vector.contracts.manager_insights_activity import WorkItem, WorkItemBundle
from vector.domains.manager_insights.extract_evidence import extract_evidence


def test_extract_evidence_splits_action_blocker_decision() -> None:
    bundle = WorkItemBundle(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        items=[
            WorkItem(
                id="w1",
                source="linear",
                type="issue",
                title="Need to fix OAuth callback parsing",
                summary="Blocked waiting on provider redirect update.",
            ),
            WorkItem(
                id="w2",
                source="notion",
                type="document",
                title="Decision: we will keep manager insight run manual",
                summary="Agreed this avoids connector noise during QA.",
            ),
        ],
    )
    out = extract_evidence(bundle)
    assert len(out.action_items) >= 1
    assert len(out.blockers) >= 1
    assert len(out.decisions) >= 1
    # hard-constraint: evidence must be non-empty quotes tied to a source work item
    for row in out.action_items + out.blockers + out.decisions:
        assert row.evidence
        assert row.source_work_item_id in {"w1", "w2"}
