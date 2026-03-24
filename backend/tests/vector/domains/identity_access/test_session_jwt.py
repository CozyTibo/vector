"""Session JWT round-trip."""

from __future__ import annotations

import uuid

import pytest

from vector.domains.identity_access.errors import SessionInvalidError
from vector.domains.identity_access.services.session_jwt import (
    decode_session_token,
    issue_session_token,
)
from vector.settings import get_settings


def test_issue_and_decode_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    s = get_settings()
    uid = uuid.UUID("018e1234-5678-7abc-8def-123456789abc")
    tid = uuid.UUID("028e1234-5678-7abc-8def-123456789abc")
    tok = issue_session_token(s, uid, tid)
    claims = decode_session_token(s, tok)
    assert claims.user_id == uid
    assert claims.tenant_id == tid


def test_decode_rejects_garbage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    s = get_settings()
    with pytest.raises(SessionInvalidError):
        decode_session_token(s, "not-a-jwt")
