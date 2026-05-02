"""§6 Step 38 — POST …/apply with dry_run=false (gated live apply + receipt)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.contracts.manager_insights_activity import DecisionDefaultAction, DecisionItem
from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
from vector.infrastructure.db.repositories import manager_insight_decisions as mid_repo
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.settings import get_settings


@pytest.mark.integration
def test_manager_insight_apply_live_noop_persists_receipt(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step38-admin-test-password")
    monkeypatch.setenv("VECTOR_MANAGER_INSIGHTS_LIVE_APPLY_ENABLED", "1")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step38 Co",
        primary_email="s38@example.com",
        email_domain="example.com",
        slug=f"s38-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()
    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:step38-noop",
        gap_id="g",
        gap_type="blocker_not_tracked",
        decision_type="BLOCKER_ESCALATION",
        title="t",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 5, 3, 10, 0, 0, tzinfo=UTC),
        run_id=run_id,
        status="proposed",
    )
    mid_repo.insert_decision_items_bulk(db_session, tenant_id=tenant.id, items=[item], ranks=[1])
    db_session.flush()
    pk = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=tenant.id,
        engine_decision_id=item.id,
    )

    auth = ("x", "step38-admin-test-password")
    url = f"/admin/tenants/{tenant.id}/manager-insight/decisions/{pk}/apply"
    r = client.post(url, auth=auth, json={"dry_run": False})
    assert r.status_code == 200
    body = r.json()
    assert body["dry_run"] is False
    assert body["decision_status"] == "completed"
    assert body["receipt"]["ok"] is True
    assert body["receipt"].get("kind") == "noop"

    row = db_session.get(ManagerInsightDecision, pk)
    assert row is not None
    assert row.status == "completed"
    assert row.receipt is not None
    assert row.receipt.get("kind") == "noop"


@pytest.mark.integration
def test_manager_insight_apply_live_slack_mocked_one_call_and_receipt(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step38-admin-test-password")
    monkeypatch.setenv("VECTOR_MANAGER_INSIGHTS_LIVE_APPLY_ENABLED", "1")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step38b Co",
        primary_email="s38b@example.com",
        email_domain="example.com",
        slug=f"s38b-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()

    user = User(
        email=f"u38-{uuid.uuid4().hex[:10]}@example.com",
        full_name="Step38 User",
    )
    db_session.add(user)
    db_session.flush()

    slack_repo.upsert_slack_oauth_connection(
        db_session,
        tenant_id=tenant.id,
        connected_by_user_id=user.id,
        bot_access_token="xoxb-test-token",
        team_id="T_STEP38",
        team_name="Step38 Workspace",
        scope="chat:write",
    )

    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:step38-slack",
        gap_id="g2",
        gap_type="blocker_not_tracked",
        decision_type="BLOCKER_ESCALATION",
        title="Slack decision",
        rationale="r",
        default_action=DecisionDefaultAction(
            kind="post_message",
            connector="slack",
            payload_template={"channel": "C01234567", "text": "coordination apply test"},
        ),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 5, 3, 11, 0, 0, tzinfo=UTC),
        run_id=run_id,
        status="proposed",
    )
    mid_repo.insert_decision_items_bulk(db_session, tenant_id=tenant.id, items=[item], ranks=[1])
    db_session.flush()
    pk = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=tenant.id,
        engine_decision_id=item.id,
    )

    auth = ("x", "step38-admin-test-password")
    url = f"/admin/tenants/{tenant.id}/manager-insight/decisions/{pk}/apply"

    def fake_slack(*, bot_token: str, channel: str, text: str) -> dict[str, object]:
        assert bot_token == "xoxb-test-token"
        assert channel == "C01234567"
        assert "coordination" in text
        return {"ok": True, "ts": "1111.2222", "channel": "C01234567"}

    with patch(
        "vector.domains.manager_insights.apply_decision_live.slack_chat_post_message",
        side_effect=fake_slack,
    ) as m_slack:
        r = client.post(url, auth=auth, json={"dry_run": False})
    assert m_slack.call_count == 1
    assert r.status_code == 200
    body = r.json()
    assert body["dry_run"] is False
    assert body["decision_status"] == "completed"
    assert body["receipt"]["ok"] is True
    assert body["receipt"]["message_ts"] == "1111.2222"

    row = db_session.get(ManagerInsightDecision, pk)
    assert row is not None
    assert row.receipt is not None
    assert row.receipt.get("ok") is True
    assert row.status == "completed"


@pytest.mark.integration
def test_manager_insight_apply_live_unsupported_returns_501(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step38-admin-test-password")
    monkeypatch.setenv("VECTOR_MANAGER_INSIGHTS_LIVE_APPLY_ENABLED", "1")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step38c Co",
        primary_email="s38c@example.com",
        email_domain="example.com",
        slug=f"s38c-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()
    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:step38-gh",
        gap_id="g3",
        gap_type="blocker_not_tracked",
        decision_type="BLOCKER_ESCALATION",
        title="gh",
        rationale="r",
        default_action=DecisionDefaultAction(
            kind="post_message",
            connector="github",
            payload_template={},
        ),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 5, 3, 12, 0, 0, tzinfo=UTC),
        run_id=run_id,
        status="proposed",
    )
    mid_repo.insert_decision_items_bulk(db_session, tenant_id=tenant.id, items=[item], ranks=[1])
    db_session.flush()
    pk = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=tenant.id,
        engine_decision_id=item.id,
    )

    auth = ("x", "step38-admin-test-password")
    url = f"/admin/tenants/{tenant.id}/manager-insight/decisions/{pk}/apply"
    r = client.post(url, auth=auth, json={"dry_run": False})
    assert r.status_code == 501

    row = db_session.get(ManagerInsightDecision, pk)
    assert row is not None
    assert row.receipt is None
    assert row.status == "proposed"
