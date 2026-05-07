"""Integration: admin connector helpers use cortex runtime (DATABASE_URL required)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"adm-{uuid.uuid4().hex[:10]}@admincx.example", full_name="Admin CX")
    tenant = Tenant(
        company_name="Admin CX",
        primary_email=user.email,
        email_domain="admincx.example",
        slug=f"acx-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id, user.id


def test_admin_disconnect_unknown_provider_returns_404(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()

    tenant_id, _ = _tenant_with_owner(db_session)

    r = client.delete(
        f"/admin/tenants/{tenant_id}/connections/not_a_connector",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 404


def test_admin_connect_link_slack_returns_503_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    for key in ("SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET", "SLACK_SIGNING_SECRET"):
        monkeypatch.setenv(key, "")
    get_settings.cache_clear()

    tenant_id, _ = _tenant_with_owner(db_session)

    r = client.get(
        f"/admin/tenants/{tenant_id}/connections/slack/connect-link",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 503


def test_admin_list_connections_empty(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()

    tenant_id, _ = _tenant_with_owner(db_session)

    r = client.get(
        f"/admin/tenants/{tenant_id}/connections",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["items"] == []
