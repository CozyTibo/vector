"""Integration tests: OAuth callback and /me (requires DATABASE_URL)."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.identity_access.services.session_jwt import issue_session_token
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def test_me_unauthenticated(client: TestClient) -> None:
    response = client.get("/me")
    assert response.status_code == 401


def test_google_oauth_flow_creates_tenant_and_session(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-google-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-google-secret")
    get_settings.cache_clear()

    from vector.domains.identity_access.services import google_oauth as go

    uid_email = f"oauth-{uuid.uuid4().hex[:10]}@acme.example"

    def fake_exchange(
        _settings: Any,
        *,
        code: str,
        code_verifier: str,
    ) -> go.GoogleProfile:
        _ = code, code_verifier
        return go.GoogleProfile(
            subject=f"google-{uuid.uuid4().hex}",
            email=uid_email,
            full_name="OAuth User",
        )

    monkeypatch.setattr(go, "exchange_code_for_profile", fake_exchange)

    r1 = client.get("/auth/google/start", follow_redirects=False)
    assert r1.status_code == 302
    loc = r1.headers["location"]
    assert "accounts.google.com" in loc
    state = parse_qs(urlparse(loc).query)["state"][0]

    r2 = client.get(
        "/auth/google/callback",
        params={"code": "fake-auth-code", "state": state},
        follow_redirects=False,
    )
    assert r2.status_code == 302
    assert "oauth_ok=1" in r2.headers["location"]

    r3 = client.get("/me")
    assert r3.status_code == 200
    body = r3.json()
    assert body["email"] == uid_email
    assert body["role"] == "owner"
    assert body["tenant_slug"].startswith("acme-example")
    assert body.get("onboarding_completed") is False
    assert body.get("connected_connectors") == []
    assert body.get("use_mock_connectors") is False


def test_me_rejects_session_for_wrong_tenant(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()

    user = User(email=f"iso-{uuid.uuid4().hex}@x.example", full_name="Iso User")
    tenant_a = Tenant(
        company_name="A",
        primary_email=user.email,
        email_domain="x.example",
        slug=f"a-{uuid.uuid4().hex[:8]}",
        status="active",
    )
    tenant_b = Tenant(
        company_name="B",
        primary_email="b@x.example",
        email_domain="x.example",
        slug=f"b-{uuid.uuid4().hex[:8]}",
        status="active",
    )
    db_session.add_all([user, tenant_a, tenant_b])
    db_session.flush()
    db_session.add(
        TenantMembership(tenant_id=tenant_a.id, user_id=user.id, role="owner"),
    )
    db_session.flush()

    bad_token = issue_session_token(settings, user.id, tenant_b.id)
    client.cookies.set(settings.session_cookie_name, bad_token)
    r = client.get("/me")
    assert r.status_code == 403


def test_register_and_login_with_password(client: TestClient) -> None:
    email = f"pw-{uuid.uuid4().hex[:12]}@example.com"
    reg = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "secure-pass-1",
            "full_name": "Password User",
            "company_name": "PW Corp",
        },
    )
    assert reg.status_code == 200
    me = client.get("/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == email
    assert body["company_name"] == "PW Corp"
    assert body.get("onboarding_completed") is False
    assert body.get("connected_connectors") == []
    assert body.get("use_mock_connectors") is False

    out = client.post("/auth/logout")
    assert out.status_code == 204
    assert client.get("/me").status_code == 401

    log = client.post("/auth/login", json={"email": email, "password": "secure-pass-1"})
    assert log.status_code == 200
    me2 = client.get("/me")
    assert me2.status_code == 200
    assert me2.json()["email"] == email


def test_register_duplicate_email_conflict(client: TestClient) -> None:
    email = f"dup-{uuid.uuid4().hex[:12]}@example.com"
    body = {"email": email, "password": "secure-pass-1"}
    assert client.post("/auth/register", json=body).status_code == 200
    dup = client.post("/auth/register", json=body)
    assert dup.status_code == 409


def test_login_wrong_password(client: TestClient) -> None:
    email = f"bad-{uuid.uuid4().hex[:12]}@example.com"
    assert (
        client.post(
            "/auth/register",
            json={"email": email, "password": "correct-pass-9"},
        ).status_code
        == 200
    )
    client.post("/auth/logout")
    fail = client.post("/auth/login", json={"email": email, "password": "wrong-pass-here"})
    assert fail.status_code == 401
