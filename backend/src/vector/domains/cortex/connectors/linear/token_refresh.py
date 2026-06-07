"""Refresh expired Linear OAuth access tokens before connector sync."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.linear.errors import LinearOAuthError
from vector.domains.cortex.connectors.linear.http_client import (
    refresh_linear_access_token,
    token_expires_at,
)
from vector.infrastructure.db.repositories.linear_connection import LinearTenantLink
from vector.settings import Settings

_LOGGER = logging.getLogger(__name__)

_DEFAULT_SKEW_SECONDS = 300


def ensure_linear_access_token(
    session: Session,
    settings: Settings,
    link: LinearTenantLink,
    *,
    skew_seconds: int = _DEFAULT_SKEW_SECONDS,
) -> str:
    """Return a valid access token, refreshing with ``refresh_token`` when near expiry."""
    detail = link.detail
    expires = detail.token_expires_at
    now = datetime.now(tz=UTC)
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires > now + timedelta(seconds=skew_seconds):
            return detail.access_token

    refresh = (detail.refresh_token or "").strip()
    if not refresh:
        _LOGGER.warning(
            "linear access token expired without refresh_token tenant_id=%s connection_id=%s",
            link.tenant_id,
            detail.connection_id,
        )
        return detail.access_token

    try:
        tok = refresh_linear_access_token(settings, refresh)
    except LinearOAuthError:
        _LOGGER.warning(
            "linear token refresh failed tenant_id=%s connection_id=%s",
            link.tenant_id,
            detail.connection_id,
            exc_info=True,
        )
        raise

    detail.access_token = tok.access_token
    if tok.refresh_token:
        detail.refresh_token = tok.refresh_token
    detail.token_expires_at = token_expires_at(tok.expires_in)
    session.flush()
    _LOGGER.info(
        "linear access token refreshed tenant_id=%s connection_id=%s expires_at=%s",
        link.tenant_id,
        detail.connection_id,
        detail.token_expires_at,
    )
    return detail.access_token
