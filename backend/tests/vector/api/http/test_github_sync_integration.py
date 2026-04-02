"""Integration: POST /connectors/github/sync (session + optional mock)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.application.services import connector_sync
from vector.domains.identity_access.services.session_jwt import issue_session_token
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
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


def _session_user_tenant(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> tuple[Any, Any, Any]:
    pem = _rsa_pem()
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    monkeypatch.setenv("GITHUB_APP_ID", "1")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", pem)
    monkeypatch.setenv("GITHUB_APP_SLUG", "vector-test")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "sec")
    get_settings.cache_clear()
    settings = get_settings()

    user = User(email=f"sync-{uuid.uuid4().hex[:10]}@t.example", full_name="S")
    tenant = Tenant(
        company_name="S Co",
        primary_email=user.email,
        email_domain="t.example",
        slug=f"s-{uuid.uuid4().hex[:8]}",
        status="active",
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(
        TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"),
    )
    db_session.flush()
    tok = issue_session_token(settings, user.id, tenant.id)
    client.cookies.set(settings.session_cookie_name, tok)
    return settings, user, tenant


def test_github_sync_unauthenticated(client: TestClient) -> None:
    assert client.post("/connectors/github/sync").status_code == 401


def test_github_ingestion_runs_unauthenticated(client: TestClient) -> None:
    assert client.get("/connectors/github/ingestion/runs").status_code == 401


def test_github_ingestion_records_unauthenticated(client: TestClient) -> None:
    rid = uuid.uuid4()
    assert client.get(f"/connectors/github/ingestion/runs/{rid}/records").status_code == 401


def test_github_sync_not_connected_returns_400(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    _session_user_tenant(monkeypatch, client, db_session)
    r = client.post("/connectors/github/sync")
    assert r.status_code == 400
    assert "not connected" in (r.json().get("detail") or "").lower()


def test_github_sync_ok_when_core_mocked(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    _session_user_tenant(monkeypatch, client, db_session)
    run_id = uuid.uuid4()
    mock_run = MagicMock()
    mock_run.id = run_id
    mock_run.connection_id = uuid.uuid4()
    mock_run.status = "succeeded"
    mock_run.error_summary = None
    mock_run.stats = {"records_written": 42}

    def _stub(
        session: Session,
        settings: Any,
        tenant_id: uuid.UUID,
    ) -> MagicMock:
        return mock_run

    monkeypatch.setattr(connector_sync, "run_github_poll_sync_with_drains", _stub)
    r = client.post("/connectors/github/sync")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == str(run_id)
    assert body["status"] == "succeeded"
    assert body["error_summary"] is None
    assert body["stats"] == {"records_written": 42}
    assert body.get("accepted_async") is False


def test_github_sync_async_returns_202_when_flag_on(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    _session_user_tenant(monkeypatch, client, db_session)
    monkeypatch.setenv("INGESTION_ASYNC_GITHUB", "true")
    get_settings.cache_clear()

    run_id = uuid.uuid4()

    def _fake_enqueue(session: Session, *, tenant_id: uuid.UUID) -> MagicMock:
        m = MagicMock()
        m.id = run_id
        m.connection_id = uuid.uuid4()
        m.status = "running"
        m.error_summary = None
        m.stats = None
        return m

    monkeypatch.setattr(connector_sync, "enqueue_github_poll_sync", _fake_enqueue)
    r = client.post("/connectors/github/sync")
    assert r.status_code == 202
    body = r.json()
    assert body["run_id"] == str(run_id)
    assert body["status"] == "running"
    assert body["accepted_async"] is True
