"""§6 Step 42 — policy aggregates → DecisionSortLearning (integration)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from vector.domains.manager_insights.decision_sort_learning import load_decision_sort_learning
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import manager_insight_outcomes as mio_repo


@pytest.mark.integration
def test_load_decision_sort_learning_suppress_from_policy_counter(db_session: Session) -> None:
    tenant = Tenant(
        company_name="Step42 Co",
        primary_email="step42@example.com",
        email_domain="example.com",
        slug=f"step42-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()

    as_of = datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC)
    mio_repo.insert_manager_insight_policy_counter_row(
        db_session,
        tenant_id=tenant.id,
        dimension="gap_type:expected_not_executed",
        window_start=datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
        false_positive_count=0,
        suppress_until=datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC),
    )
    db_session.commit()

    learning = load_decision_sort_learning(
        db_session,
        tenant_id=tenant.id,
        as_of=as_of,
        window_days=30,
    )
    assert learning.demotion_for_gap_type("expected_not_executed") >= 10_000
    assert "expected_not_executed" in learning.gap_demotions_for_qa()
