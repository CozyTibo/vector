"""Linear OAuth token refresh before ingestion sync."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from vector.domains.cortex.connectors.linear.errors import LinearOAuthError
from vector.domains.cortex.connectors.linear.http_client import LinearTokenResponse
from vector.domains.cortex.connectors.linear.token_refresh import ensure_linear_access_token
from vector.infrastructure.db.repositories.linear_connection import LinearTenantLink


def _link(*, expires_at: datetime | None, refresh: str | None = "refresh-abc") -> LinearTenantLink:
    connection = MagicMock()
    connection.tenant_id = uuid.uuid4()
    detail = MagicMock()
    detail.connection_id = uuid.uuid4()
    detail.access_token = "old-access"
    detail.refresh_token = refresh
    detail.token_expires_at = expires_at
    return LinearTenantLink(connection=connection, detail=detail)


def test_ensure_linear_access_token_returns_cached_when_fresh() -> None:
    link = _link(expires_at=datetime.now(tz=UTC) + timedelta(hours=2))
    session = MagicMock()
    settings = MagicMock()
    assert ensure_linear_access_token(session, settings, link) == "old-access"
    session.flush.assert_not_called()


def test_ensure_linear_access_token_refreshes_when_expired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    link = _link(expires_at=datetime.now(tz=UTC) - timedelta(minutes=5))
    session = MagicMock()
    settings = MagicMock()

    monkeypatch.setattr(
        "vector.domains.cortex.connectors.linear.token_refresh.refresh_linear_access_token",
        lambda _settings, _refresh: LinearTokenResponse(
            access_token="new-access",
            refresh_token="new-refresh",
            expires_in=3600,
        ),
    )

    token = ensure_linear_access_token(session, settings, link)
    assert token == "new-access"
    assert link.detail.access_token == "new-access"
    assert link.detail.refresh_token == "new-refresh"
    assert link.detail.token_expires_at is not None
    session.flush.assert_called_once()


def test_ensure_linear_access_token_without_refresh_returns_stale_token() -> None:
    link = _link(expires_at=datetime.now(tz=UTC) - timedelta(hours=1), refresh=None)
    session = MagicMock()
    settings = MagicMock()
    assert ensure_linear_access_token(session, settings, link) == "old-access"
    session.flush.assert_not_called()


def test_ensure_linear_access_token_raises_when_refresh_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    link = _link(expires_at=datetime.now(tz=UTC) - timedelta(minutes=1))
    session = MagicMock()
    settings = MagicMock()

    def _fail(_settings: MagicMock, _refresh: str) -> LinearTokenResponse:
        raise LinearOAuthError("refresh denied")

    monkeypatch.setattr(
        "vector.domains.cortex.connectors.linear.token_refresh.refresh_linear_access_token",
        _fail,
    )

    with pytest.raises(LinearOAuthError):
        ensure_linear_access_token(session, settings, link)
