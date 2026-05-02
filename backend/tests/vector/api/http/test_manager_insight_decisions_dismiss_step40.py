"""§6 Step 40 — POST /admin/tenants/{id}/manager-insight/decisions/{id}/dismiss (integration)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.contracts.manager_insights_activity import DecisionDefaultAction, DecisionItem
from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision
from vector.infrastructure.db.models.manager_insight_outcome import ManagerInsightOutcome
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import manager_insight_decisions as mid_repo
from vector.settings import get_settings


@pytest.mark.integration
def test_manager_insight_dismiss_creates_outcome_and_updates_status(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step40-admin-test-password")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step40 Co",
        primary_email="s40@example.com",
        email_domain="example.com",
        slug=f"s40-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()

    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:step40-dismiss",
        gap_id="gap-d",
        gap_type="expected_not_executed",
        decision_type="LINK_OR_CLOSE_COMMITMENT",
        title="Dismiss me",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 5, 4, 10, 0, 0, tzinfo=UTC),
        run_id=run_id,
        status="proposed",
    )
    mid_repo.insert_decision_items_bulk(db_session, tenant_id=tenant.id, items=[item], ranks=[1])
    db_session.flush()
    pk = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=tenant.id,
        engine_decision_id=item.id,
    )

    auth = ("x", "step40-admin-test-password")
    url = f"/admin/tenants/{tenant.id}/manager-insight/decisions/{pk}/dismiss"
    r = client.post(
        url,
        auth=auth,
        json={"user_attribution": "qa-admin", "false_positive": True, "ground_truth": {"k": 1}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision_status"] == "dismissed"
    assert body["idempotent"] is False
    assert body["outcome"]["outcome_type"] == "dismissed"
    assert body["outcome"]["false_positive"] is True
    assert body["outcome"]["user_attribution"] == "qa-admin"
    assert body["outcome"]["ground_truth"] == {"k": 1}

    row = db_session.scalar(select(ManagerInsightDecision).where(ManagerInsightDecision.id == pk))
    assert row is not None
    assert row.status == "dismissed"

    oc = db_session.scalar(
        select(ManagerInsightOutcome).where(ManagerInsightOutcome.decision_id == pk),
    )
    assert oc is not None
    assert oc.outcome_type == "dismissed"

    r2 = client.post(url, auth=auth, json={})
    assert r2.status_code == 200
    assert r2.json()["idempotent"] is True
    assert r2.json()["outcome"]["id"] == body["outcome"]["id"]


@pytest.mark.integration
def test_manager_insight_dismiss_terminal_returns_409(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step40b-admin-test-password")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step40b Co",
        primary_email="s40b@example.com",
        email_domain="example.com",
        slug=f"s40b-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()

    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:step40-term",
        gap_id="gap-t",
        gap_type="blocker_not_tracked",
        decision_type="BLOCKER_ESCALATION",
        title="Done",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 5, 4, 11, 0, 0, tzinfo=UTC),
        run_id=run_id,
        status="completed",
    )
    mid_repo.insert_decision_items_bulk(db_session, tenant_id=tenant.id, items=[item], ranks=[1])
    db_session.flush()
    pk = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=tenant.id,
        engine_decision_id=item.id,
    )

    r = client.post(
        f"/admin/tenants/{tenant.id}/manager-insight/decisions/{pk}/dismiss",
        auth=("x", "step40b-admin-test-password"),
        json={},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["status"] == "completed"


@pytest.mark.integration
def test_manager_insight_dismiss_unknown_decision_404(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step40c-admin-test-password")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step40c Co",
        primary_email="s40c@example.com",
        email_domain="example.com",
        slug=f"s40c-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()

    missing = uuid.uuid4()
    r = client.post(
        f"/admin/tenants/{tenant.id}/manager-insight/decisions/{missing}/dismiss",
        auth=("x", "step40c-admin-test-password"),
        json={},
    )
    assert r.status_code == 404
