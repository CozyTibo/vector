"""Integration: GitHub connect flow (DATABASE_URL required)."""

from __future__ import annotations

import uuid
from typing import Any, cast

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.connectors.github.http_client import GitHubUserTokenExchange
from vector.domains.connectors.github.install_state import create_install_state_token
from vector.domains.identity_access.services.session_jwt import issue_session_token
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _rsa_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode()


def _github_item(payload: dict[str, Any]) -> dict[str, Any] | None:
    for raw in payload["items"]:
        if not isinstance(raw, dict):
            continue
        if raw.get("provider") == "github":
            return cast(dict[str, Any], raw)
    return None


def test_connectors_unauthenticated(client: TestClient) -> None:
    assert client.get("/connectors").status_code == 401


def test_github_disconnect_unauthenticated(client: TestClient) -> None:
    assert client.delete("/connectors/github").status_code == 401


def test_linear_disconnect_unauthenticated(client: TestClient) -> None:
    assert client.delete("/connectors/linear").status_code == 401


def test_github_status_not_configured(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    # Empty string in os.environ overrides docker/.env-injected values; delenv alone can
    # still let pydantic-settings repopulate from env_file for missing keys.
    for key in (
        "GITHUB_APP_ID",
        "GITHUB_APP_PRIVATE_KEY",
        "GITHUB_APP_PRIVATE_KEY_PATH",
        "GITHUB_APP_SLUG",
        "GITHUB_CLIENT_ID",
        "GITHUB_CLIENT_SECRET",
        "LINEAR_CLIENT_ID",
        "LINEAR_CLIENT_SECRET",
    ):
        monkeypatch.setenv(key, "")
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()

    user = User(email=f"gh-{uuid.uuid4().hex[:10]}@t.example", full_name="T")
    tenant = Tenant(
        company_name="T Co",
        primary_email=user.email,
        email_domain="t.example",
        slug=f"t-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(
        TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"),
    )
    db_session.flush()

    tok = issue_session_token(settings, user.id, tenant.id)
    client.cookies.set(settings.session_cookie_name, tok)
    r = client.get("/connectors")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) >= 2
    gh = _github_item(body)
    assert gh is not None
    assert gh["connector_configured"] is False
    assert gh["connected"] is False
    lin = next((i for i in body["items"] if i["provider"] == "linear"), None)
    assert lin is not None
    assert lin["connector_configured"] is False


def test_github_install_redirect_when_configured(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    pem = _rsa_pem()
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    monkeypatch.setenv("GITHUB_APP_ID", "99")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", pem)
    monkeypatch.setenv("GITHUB_APP_SLUG", "vector-test-app")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "Iv1.clientid")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "secret")
    get_settings.cache_clear()
    settings = get_settings()

    user = User(email=f"gh-{uuid.uuid4().hex[:10]}@t.example", full_name="T")
    tenant = Tenant(
        company_name="T Co",
        primary_email=user.email,
        email_domain="t.example",
        slug=f"t-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(
        TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"),
    )
    db_session.flush()

    tok = issue_session_token(settings, user.id, tenant.id)
    client.cookies.set(settings.session_cookie_name, tok)

    r = client.get("/connectors/github/install", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers["location"]
    assert "github.com/apps/vector-test-app/installations/new" in loc
    assert "state=" in loc


def test_github_install_service_unavailable_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    for key in (
        "GITHUB_APP_ID",
        "GITHUB_APP_PRIVATE_KEY",
        "GITHUB_APP_SLUG",
        "GITHUB_CLIENT_ID",
        "GITHUB_CLIENT_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()

    user = User(email=f"gh-{uuid.uuid4().hex[:10]}@t.example", full_name="T")
    tenant = Tenant(
        company_name="T Co",
        primary_email=user.email,
        email_domain="t.example",
        slug=f"t-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(
        TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"),
    )
    db_session.flush()

    tok = issue_session_token(settings, user.id, tenant.id)
    client.cookies.set(settings.session_cookie_name, tok)

    r = client.get("/connectors/github/install", follow_redirects=False)
    assert r.status_code == 503


def test_github_callback_persists_connection(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    from vector.domains.connectors.github import install_flow

    pem = _rsa_pem()
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    monkeypatch.setenv("GITHUB_APP_ID", "1")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", pem)
    monkeypatch.setenv("GITHUB_APP_SLUG", "vector-dev")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "sec")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:5173")
    get_settings.cache_clear()
    settings = get_settings()

    user = User(email=f"gh-{uuid.uuid4().hex[:10]}@t.example", full_name="T")
    tenant = Tenant(
        company_name="T Co",
        primary_email=user.email,
        email_domain="t.example",
        slug=f"t-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(
        TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"),
    )
    db_session.flush()

    tok = issue_session_token(settings, user.id, tenant.id)
    client.cookies.set(settings.session_cookie_name, tok)

    state = create_install_state_token(settings, tenant.id, user.id)

    def fake_exchange(_settings: Any, _code: str) -> GitHubUserTokenExchange:
        return GitHubUserTokenExchange(
            access_token="tok",
            refresh_token=None,
            expires_in=3600,
        )

    def fake_fetch(_settings: Any, installation_id: int) -> dict[str, Any]:
        return {
            "id": installation_id,
            "account": {"id": 777, "login": "acme-org", "type": "Organization"},
        }

    monkeypatch.setattr(install_flow, "exchange_github_user_code", fake_exchange)
    monkeypatch.setattr(install_flow, "fetch_github_installation", fake_fetch)

    client.cookies.clear()
    r = client.get(
        "/connectors/github/callback",
        params={"code": "c1", "state": state, "installation_id": 42_424_242},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "github_connected=1" in r.headers["location"]

    row = gh_repo.get_github_connection_for_tenant(db_session, tenant.id)
    assert row is not None
    assert row.installation_id == 42_424_242
    assert row.account_login == "acme-org"
    assert row.account_type == "Organization"

    client.cookies.set(settings.session_cookie_name, tok)
    st = client.get("/connectors")
    assert st.status_code == 200
    gh = _github_item(st.json())
    assert gh is not None
    assert gh["connected"] is True
    assert gh["details"]["account_login"] == "acme-org"

    disc = client.delete("/connectors/github")
    assert disc.status_code == 204
    assert gh_repo.get_github_connection_for_tenant(db_session, tenant.id) is None

    st2 = client.get("/connectors")
    assert st2.status_code == 200
    gh2 = _github_item(st2.json())
    assert gh2 is not None
    assert gh2["connected"] is False

    disc2 = client.delete("/connectors/github")
    assert disc2.status_code == 204


def test_disconnect_unknown_provider_returns_404(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()

    user = User(email=f"gh-{uuid.uuid4().hex[:10]}@t.example", full_name="T")
    tenant = Tenant(
        company_name="T Co",
        primary_email=user.email,
        email_domain="t.example",
        slug=f"t-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(
        TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"),
    )
    db_session.flush()

    tok = issue_session_token(settings, user.id, tenant.id)
    client.cookies.set(settings.session_cookie_name, tok)
    assert client.delete("/connectors/not_a_provider").status_code == 404
