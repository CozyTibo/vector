"""§6 Step 37 — POST /admin/tenants/{id}/manager-insight/decisions/{id}/apply (dry_run only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.contracts.manager_insights_activity import DecisionDefaultAction, DecisionItem
from vector.domains.manager_insights import apply_decision_dry_run as dry_mod
from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import manager_insight_decisions as mid_repo
from vector.settings import get_settings


@pytest.mark.integration
def test_manager_insight_apply_dry_run_returns_planned_payload(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step37-admin-test-password")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step37 Co",
        primary_email="s37@example.com",
        email_domain="example.com",
        slug=f"s37-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()

    run_id = uuid.uuid4()
    items = [
        DecisionItem(
            id="engine:decision:step37-apply",
            gap_id="gap-apply-1",
            gap_type="blocker_not_tracked",
            decision_type="BLOCKER_ESCALATION",
            title="Escalate blocker",
            rationale="r",
            default_action=DecisionDefaultAction(
                kind="post_message",
                connector="slack",
                payload_template={"channel": "C1", "text": "hello"},
            ),
            required_inputs={"text": "override"},
            evidence_refs=[],
            signal_refs=[],
            created_at=datetime(2026, 5, 2, 10, 0, 0, tzinfo=UTC),
            run_id=run_id,
            status="proposed",
        ),
    ]
    mid_repo.insert_decision_items_bulk(db_session, tenant_id=tenant.id, items=items, ranks=[1])
    db_session.flush()

    decision_pk = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=tenant.id,
        engine_decision_id=items[0].id,
    )

    auth = ("x", "step37-admin-test-password")
    url = f"/admin/tenants/{tenant.id}/manager-insight/decisions/{decision_pk}/apply"

    with patch(
        "vector.api.http.routes.admin.plan_manager_insight_apply_dry_run",
        wraps=dry_mod.plan_manager_insight_apply_dry_run,
    ) as m_plan:
        r = client.post(url, auth=auth, json={"dry_run": True})
    assert r.status_code == 200
    assert m_plan.call_count == 1

    body = r.json()
    assert body["dry_run"] is True
    assert body["decision_id"] == str(decision_pk)
    assert body["tenant_id"] == str(tenant.id)
    assert body["decision_status"] == "proposed"
    assert body["default_action"]["kind"] == "post_message"
    assert body["default_action"]["connector"] == "slack"
    planned = body["planned_payload"]
    assert planned["external_io"] is False
    assert planned["connector"] == "slack"
    # Persist maps DecisionItem.dominant into required_inputs as narrative_dominant (see manager_insight_decision_from_item).
    assert planned["merged_arguments"] == {
        "channel": "C1",
        "text": "override",
        "narrative_dominant": False,
    }
    assert isinstance(body["note"], str) and len(body["note"]) > 0


@pytest.mark.integration
def test_manager_insight_apply_live_disabled_returns_403(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step37-admin-test-password")
    monkeypatch.delenv("VECTOR_MANAGER_INSIGHTS_LIVE_APPLY_ENABLED", raising=False)
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step37b Co",
        primary_email="s37b@example.com",
        email_domain="example.com",
        slug=f"s37b-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()
    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:step37-live",
        gap_id="g",
        gap_type="blocker_not_tracked",
        decision_type="BLOCKER_ESCALATION",
        title="t",
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

    auth = ("x", "step37-admin-test-password")
    url = f"/admin/tenants/{tenant.id}/manager-insight/decisions/{pk}/apply"
    r = client.post(url, auth=auth, json={"dry_run": False})
    assert r.status_code == 403


@pytest.mark.integration
def test_manager_insight_apply_dry_run_wrong_tenant_404(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step37-admin-test-password")
    get_settings.cache_clear()

    t_a = Tenant(
        company_name="A",
        primary_email="a@example.com",
        email_domain="example.com",
        slug=f"a-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    t_b = Tenant(
        company_name="B",
        primary_email="b@example.com",
        email_domain="example.com",
        slug=f"b-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add_all([t_a, t_b])
    db_session.flush()
    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:step37-wrong-tenant",
        gap_id="g",
        gap_type="blocker_not_tracked",
        decision_type="BLOCKER_ESCALATION",
        title="t",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 5, 2, 10, 0, 0, tzinfo=UTC),
        run_id=run_id,
        status="proposed",
    )
    mid_repo.insert_decision_items_bulk(db_session, tenant_id=t_a.id, items=[item], ranks=[1])
    db_session.flush()
    pk = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=t_a.id,
        engine_decision_id=item.id,
    )

    auth = ("x", "step37-admin-test-password")
    url = f"/admin/tenants/{t_b.id}/manager-insight/decisions/{pk}/apply"
    r = client.post(url, auth=auth, json={"dry_run": True})
    assert r.status_code == 404


@pytest.mark.integration
def test_manager_insight_apply_dry_run_invalid_default_action_422(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step37-admin-test-password")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step37c Co",
        primary_email="s37c@example.com",
        email_domain="example.com",
        slug=f"s37c-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()
    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:step37-bad-action",
        gap_id="g",
        gap_type="blocker_not_tracked",
        decision_type="BLOCKER_ESCALATION",
        title="t",
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
    row = db_session.get(ManagerInsightDecision, pk)
    assert row is not None
    row.default_action = {"kind": "noop", "connector": "zoom", "payload_template": {}}
    db_session.flush()

    auth = ("x", "step37-admin-test-password")
    url = f"/admin/tenants/{tenant.id}/manager-insight/decisions/{pk}/apply"
    r = client.post(url, auth=auth, json={"dry_run": True})
    assert r.status_code == 422


@pytest.mark.integration
def test_manager_insight_apply_dry_run_no_admin_connector_enqueue(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§6.2: dry-run must not enqueue connector sync jobs used elsewhere on the admin router."""
    monkeypatch.setenv("ADMIN_PASSWORD", "step37-admin-test-password")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step37d Co",
        primary_email="s37d@example.com",
        email_domain="example.com",
        slug=f"s37d-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()
    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:step37-no-connector",
        gap_id="g",
        gap_type="blocker_not_tracked",
        decision_type="BLOCKER_ESCALATION",
        title="t",
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

    auth = ("x", "step37-admin-test-password")
    url = f"/admin/tenants/{tenant.id}/manager-insight/decisions/{pk}/apply"

    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("connector_sync must not run on dry-run apply")

    admin_cs = "vector.api.http.routes.admin.connector_sync"
    with (
        patch(f"{admin_cs}.enqueue_github_poll_sync", side_effect=boom),
        patch(f"{admin_cs}.enqueue_linear_poll_sync", side_effect=boom),
    ):
        r = client.post(url, auth=auth, json={"dry_run": True})
    assert r.status_code == 200
    assert r.json()["planned_payload"]["external_io"] is False
