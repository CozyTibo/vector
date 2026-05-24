"""Operator admin v2 queues + async graph refresh (R4)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"opr4-{uuid.uuid4().hex[:10]}@example.com", full_name="Op R4")
    tenant = Tenant(
        company_name="Op R4 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"opr4-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_operator_queues_disabled_by_default(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_ADMIN_V2", "false")
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/queues")
    assert res.status_code == 404


def test_operator_queues_when_flag_enabled(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_ADMIN_V2", "true")
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(
        f"/admin/tenants/{tid}/cortex/operator/queues",
        params={"tab": "deferrals", "limit": 10, "offset": 0},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_queues_v1"
    assert body["tenant_id"] == str(tid)
    assert body["tab"] == "deferrals"
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert body["items"] == []
    assert body["counts"]["synthesis_failed"] == 0
    assert body["counts"]["tcre_queued"] == 0
    assert body["counts"]["deferrals"] == 0
    assert body["counts"]["ingestion_failed"] == 0


def test_operator_graph_snapshot_includes_component_snapshot(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_ADMIN_V2", "true")
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(f"/admin/tenants/{tid}/cortex/operator/snapshots/graph")
    assert res.status_code == 200
    body = res.json()
    assert "component_snapshot" in body
    assert body["component_snapshot"]["job_status"] == "idle"


def test_operator_graph_refresh_disabled_by_default(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_ADMIN_V2", "false")
    tid = _tenant(db_session)
    db_session.commit()
    res = client.post(f"/admin/tenants/{tid}/cortex/operator/snapshots/graph/refresh")
    assert res.status_code == 404


def test_operator_graph_refresh_enqueues(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_ADMIN_V2", "true")
    tid = _tenant(db_session)
    db_session.commit()

    mock_delay = MagicMock()
    monkeypatch.setattr(
        "app.tasks.cortex_admin_snapshot.refresh_graph_component_snapshot_task.delay",
        mock_delay,
    )

    res = client.post(f"/admin/tenants/{tid}/cortex/operator/snapshots/graph/refresh")
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_graph_component_refresh_v1"
    assert body["tenant_id"] == str(tid)
    assert body["enqueued"] is True
    assert body["job_status"] == "pending"
    mock_delay.assert_called_once_with(str(tid))

    dup = client.post(f"/admin/tenants/{tid}/cortex/operator/snapshots/graph/refresh")
    assert dup.status_code == 200
    assert dup.json()["enqueued"] is False
    assert dup.json()["hint"] == "refresh_already_in_progress"
