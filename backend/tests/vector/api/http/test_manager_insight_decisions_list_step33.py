"""§6 Steps 33–34 — GET /admin/tenants/{id}/manager-insight/decisions (integration)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.contracts.manager_insights_activity import DecisionDefaultAction, DecisionItem
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import manager_insight_decisions as mid_repo
from vector.settings import get_settings


@pytest.mark.integration
def test_manager_insight_list_decisions_pagination_and_filters(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step33-admin-test-password")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step33 Co",
        primary_email="s33@example.com",
        email_domain="example.com",
        slug=f"s33-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()

    run_keep = uuid.uuid4()
    run_other = uuid.uuid4()

    items = [
        DecisionItem(
            id="engine:decision:step33-a",
            gap_id="gap-a",
            gap_type="blocker_not_tracked",
            decision_type="BLOCKER_ESCALATION",
            title="First",
            rationale="r1",
            default_action=DecisionDefaultAction(kind="noop"),
            required_inputs={},
            evidence_refs=[],
            signal_refs=[],
            created_at=datetime(2026, 5, 1, 10, 0, 0, tzinfo=UTC),
            run_id=run_keep,
            status="proposed",
        ),
        DecisionItem(
            id="engine:decision:step33-b",
            gap_id="gap-b",
            gap_type="expected_not_executed",
            decision_type="LINK_OR_CLOSE_COMMITMENT",
            title="Second",
            rationale="r2",
            default_action=DecisionDefaultAction(kind="noop"),
            required_inputs={},
            evidence_refs=[],
            signal_refs=[],
            created_at=datetime(2026, 5, 1, 11, 0, 0, tzinfo=UTC),
            run_id=run_other,
            status="accepted",
        ),
    ]
    mid_repo.insert_decision_items_bulk(db_session, tenant_id=tenant.id, items=items, ranks=[1, 2])
    db_session.flush()

    auth = ("x", "step33-admin-test-password")
    base = f"/admin/tenants/{tenant.id}/manager-insight/decisions"

    r0 = client.get(base, auth=auth, params={"limit": 50, "offset": 0})
    assert r0.status_code == 200
    body = r0.json()
    assert body["total"] == 2
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["items"]) == 2
    types = {x["decision_type"] for x in body["items"]}
    assert types == {"BLOCKER_ESCALATION", "LINK_OR_CLOSE_COMMITMENT"}

    r_filter = client.get(base, auth=auth, params={"status": "proposed"})
    assert r_filter.status_code == 200
    fbody = r_filter.json()
    assert fbody["total"] == 1
    assert fbody["items"][0]["status"] == "proposed"

    r_run = client.get(base, auth=auth, params={"run_id": str(run_keep)})
    assert r_run.status_code == 200
    assert r_run.json()["total"] == 1
    assert r_run.json()["items"][0]["run_id"] == str(run_keep)

    r_gap_id = client.get(base, auth=auth, params={"gap_id": "gap-b"})
    assert r_gap_id.status_code == 200
    gbody = r_gap_id.json()
    assert gbody["total"] == 1
    assert gbody["items"][0]["gap_id"] == "gap-b"

    r_page = client.get(base, auth=auth, params={"limit": 1, "offset": 1})
    assert r_page.status_code == 200
    pbody = r_page.json()
    assert pbody["total"] == 2
    assert len(pbody["items"]) == 1

    r401 = client.get(base, auth=("x", "wrong"))
    assert r401.status_code == 401


@pytest.mark.integration
def test_manager_insight_list_decisions_unknown_tenant(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step33-admin-test-password")
    get_settings.cache_clear()
    missing = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    r = client.get(
        f"/admin/tenants/{missing}/manager-insight/decisions",
        auth=("x", "step33-admin-test-password"),
    )
    assert r.status_code == 404
