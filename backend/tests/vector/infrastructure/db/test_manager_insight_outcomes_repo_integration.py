"""§6 Step 39 — round-trip inserts for outcomes + policy counters (integration)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.contracts.manager_insights_activity import DecisionDefaultAction, DecisionItem
from vector.infrastructure.db.models.manager_insight_policy_counter import (
    ManagerInsightPolicyCounter,
)
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import (
    manager_insight_decisions as mid_repo,
    manager_insight_outcomes as mio_repo,
)


@pytest.mark.integration
def test_outcomes_list_and_policy_counter_roundtrip(db_session: Session) -> None:
    tenant = Tenant(
        company_name="MIO Co",
        primary_email="mio@example.com",
        email_domain="example.com",
        slug=f"mio-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()

    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:mio-1",
        gap_id="g1",
        gap_type="blocker_not_tracked",
        decision_type="BLOCKER_ESCALATION",
        title="t",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 5, 3, 9, 0, 0, tzinfo=UTC),
        run_id=run_id,
        status="proposed",
    )
    mid_repo.insert_decision_items_bulk(db_session, tenant_id=tenant.id, items=[item], ranks=[1])
    db_session.flush()
    decision_id = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=tenant.id,
        engine_decision_id=item.id,
    )

    ws = datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC)
    mio_repo.insert_manager_insight_policy_counter_row(
        db_session,
        tenant_id=tenant.id,
        dimension="gap_type:blocker_not_tracked",
        window_start=ws,
        false_positive_count=2,
        suppress_until=datetime(2026, 5, 10, 0, 0, 0, tzinfo=UTC),
    )
    mio_repo.insert_manager_insight_outcome_row(
        db_session,
        tenant_id=tenant.id,
        decision_id=decision_id,
        outcome_type="applied_success",
        observed_at=datetime(2026, 5, 3, 10, 0, 0, tzinfo=UTC),
    )
    db_session.commit()

    page = mio_repo.list_manager_insight_outcomes_for_tenant(
        db_session,
        tenant_id=tenant.id,
        limit=10,
        offset=0,
    )
    assert page.total == 1
    assert page.items[0].decision_id == decision_id
    assert page.items[0].outcome_type == "applied_success"

    pc = db_session.scalar(
        select(ManagerInsightPolicyCounter).where(
            ManagerInsightPolicyCounter.tenant_id == tenant.id,
            ManagerInsightPolicyCounter.dimension == "gap_type:blocker_not_tracked",
            ManagerInsightPolicyCounter.window_start == ws,
        )
    )
    assert pc is not None
    assert pc.false_positive_count == 2
    assert pc.suppress_until is not None
