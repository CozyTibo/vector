"""§6 Step 39 — GET /admin/tenants/{id}/manager-insight/outcomes (integration)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.contracts.manager_insights_activity import DecisionDefaultAction, DecisionItem
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import manager_insight_decisions as mid_repo
from vector.infrastructure.db.repositories import manager_insight_outcomes as mio_repo
from vector.settings import get_settings


@pytest.mark.integration
def test_manager_insight_list_outcomes_pagination(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step39-admin-test-password")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step39 Co",
        primary_email="s39@example.com",
        email_domain="example.com",
        slug=f"s39-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()

    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:step39-a",
        gap_id="gap-out",
        gap_type="expected_not_executed",
        decision_type="LINK_OR_CLOSE_COMMITMENT",
        title="Outcome parent",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 5, 2, 10, 0, 0, tzinfo=UTC),
        run_id=run_id,
        status="proposed",
    )
    mid_repo.insert_decision_items_bulk(db_session, tenant_id=tenant.id, items=[item], ranks=[1])
    db_session.flush()

    pk = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=tenant.id,
        engine_decision_id=item.id,
    )
    mio_repo.insert_manager_insight_outcome_row(
        db_session,
        tenant_id=tenant.id,
        decision_id=pk,
        outcome_type="dismissed",
        observed_at=datetime(2026, 5, 2, 11, 0, 0, tzinfo=UTC),
        false_positive=True,
        ground_truth={"note": "fp"},
        user_attribution="tester",
    )
    db_session.commit()

    auth = ("x", "step39-admin-test-password")
    base = f"/admin/tenants/{tenant.id}/manager-insight/outcomes"

    r0 = client.get(base, auth=auth, params={"limit": 50, "offset": 0})
    assert r0.status_code == 200
    body = r0.json()
    assert body["total"] == 1
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    row = body["items"][0]
    assert row["decision_id"] == str(pk)
    assert row["outcome_type"] == "dismissed"
    assert row["false_positive"] is True
    assert row["ground_truth"] == {"note": "fp"}
    assert row["user_attribution"] == "tester"

    r401 = client.get(base, auth=("x", "wrong"))
    assert r401.status_code == 401


@pytest.mark.integration
def test_manager_insight_list_outcomes_unknown_tenant(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step39-admin-test-password")
    get_settings.cache_clear()
    tid = uuid.uuid4()
    r = client.get(
        f"/admin/tenants/{tid}/manager-insight/outcomes",
        auth=("x", "step39-admin-test-password"),
    )
    assert r.status_code == 404
