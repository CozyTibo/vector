"""Unit tests for connector install ticket JWT."""

from __future__ import annotations

import uuid

import pytest

from vector.domains.identity_access.errors import SessionInvalidError
from vector.domains.identity_access.services.connector_install_ticket import (
    decode_connector_install_ticket,
    issue_connector_install_ticket,
)
from vector.domains.identity_access.services.session_jwt import issue_session_token
from vector.settings import get_settings


def test_install_ticket_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    uid = uuid.uuid4()
    tid = uuid.uuid4()
    t = issue_connector_install_ticket(settings, uid, tid, "slack")
    out = decode_connector_install_ticket(settings, t, expected_provider="slack")
    assert out.user_id == uid
    assert out.tenant_id == tid


def test_install_ticket_wrong_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    t = issue_connector_install_ticket(
        settings, uuid.uuid4(), uuid.uuid4(), "slack",
    )
    with pytest.raises(SessionInvalidError):
        decode_connector_install_ticket(settings, t, expected_provider="github")


def test_session_token_rejected_as_install_ticket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    session_jwt = issue_session_token(settings, uuid.uuid4(), uuid.uuid4())
    with pytest.raises(SessionInvalidError):
        decode_connector_install_ticket(settings, session_jwt, expected_provider="slack")
