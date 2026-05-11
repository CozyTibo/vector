"""Integration: /connectors aggregate + per-provider mounts match cortex connector runtime."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.connectors.runtime import all_runtimes_ordered
from vector.domains.identity_access.services.session_jwt import issue_session_token
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration

_EXPECTED_IDS = tuple(rt.id for rt in all_runtimes_ordered())


def _session_client(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> tuple[object, uuid.UUID, uuid.UUID]:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()

    user = User(email=f"cx-{uuid.uuid4().hex[:10]}@parity.example", full_name="Parity")
    tenant = Tenant(
        company_name="Parity Co",
        primary_email=user.email,
        email_domain="parity.example",
        slug=f"p-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()

    tok = issue_session_token(settings, user.id, tenant.id)
    client.cookies.set(settings.session_cookie_name, tok)
    return settings, tenant.id, user.id


def test_connectors_list_matches_runtime_registry_order_and_count(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    _session_client(monkeypatch, client, db_session)
    r = client.get("/connectors")
    assert r.status_code == 200
    items = r.json()["items"]
    ids = [it["provider"] for it in items]
    assert ids == list(_EXPECTED_IDS)
    assert set(ids) == set(_EXPECTED_IDS)


def test_prepare_install_accepts_each_runtime_provider(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    _session_client(monkeypatch, client, db_session)
    for pid in _EXPECTED_IDS:
        prep = client.post("/connectors/install/prepare", json={"provider": pid})
        assert prep.status_code == 200, prep.text
        body = prep.json()
        assert body["provider"] == pid
        assert isinstance(body.get("install_ticket"), str) and body["install_ticket"].strip()


def test_prepare_install_invalid_provider_rejected_by_schema(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    _session_client(monkeypatch, client, db_session)
    r = client.post("/connectors/install/prepare", json={"provider": "unknown"})
    assert r.status_code == 422


def test_each_provider_install_requires_session_or_ticket(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    # Ensure cookie cleared
    client.cookies.clear()
    for pid in _EXPECTED_IDS:
        r = client.get(f"/connectors/{pid}/install")
        assert r.status_code == 401, pid


def test_connectors_delete_unknown_provider_returns_404(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    _session_client(monkeypatch, client, db_session)
    assert client.delete("/connectors/not_a_real_connector").status_code == 404


def test_slack_oauth_callback_missing_code_returns_redirect(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    """Root-mounted Slack callback stays wired (matches SLACK_CALLBACK_URL contract)."""
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:5173")
    get_settings.cache_clear()

    r = client.get("/slack/callback", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers.get("location")
