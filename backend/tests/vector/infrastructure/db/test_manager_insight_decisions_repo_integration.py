"""§6 Step 31 — round-trip insert against PostgreSQL (integration)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.contracts.manager_insights_activity import DecisionDefaultAction, DecisionItem
from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import manager_insight_decisions as mid_repo


@pytest.mark.integration
def test_insert_decision_items_bulk_roundtrip(db_session: Session) -> None:
    tenant = Tenant(
        company_name="MID Co",
        primary_email="mid@example.com",
        email_domain="example.com",
        slug=f"mid-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()

    rid = uuid.uuid4()
    item = DecisionItem(
        id="coordination:decision:int-test",
        gap_id="gap-int",
        gap_type="expected_not_executed",
        decision_type="LINK_OR_CLOSE_COMMITMENT",
        title="Close the loop",
        rationale="Because test",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC),
        run_id=rid,
        status="proposed",
    )
    n = mid_repo.insert_decision_items_bulk(db_session, tenant_id=tenant.id, items=[item], ranks=[1])
    assert n == 1
    db_session.commit()

    pk = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=tenant.id,
        engine_decision_id=item.id,
    )
    row = db_session.scalar(select(ManagerInsightDecision).where(ManagerInsightDecision.id == pk))
    assert row is not None
    assert row.tenant_id == tenant.id
    assert row.run_id == rid
    assert row.gap_id == "gap-int"
    assert row.rank == 1
    assert row.decision_type == "LINK_OR_CLOSE_COMMITMENT"
