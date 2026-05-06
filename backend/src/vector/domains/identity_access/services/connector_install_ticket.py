"""Short-lived JWT so connector OAuth can start via full-page navigation (no Authorization header)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from vector.domains.identity_access.errors import SessionInvalidError
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.settings import Settings

_CONNECTOR_INSTALL_PURPOSE = "connector_install"
_DEFAULT_TTL_SECONDS = 180


def issue_connector_install_ticket(
    settings: Settings,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    provider: str,
) -> str:
    """Sign a short-lived token carried as ``install_ticket`` on ``GET /connectors/<p>/install``."""
    now = datetime.now(tz=UTC)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "p": provider,
        "purpose": _CONNECTOR_INSTALL_PURPOSE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=_DEFAULT_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_connector_install_ticket(
    settings: Settings,
    token: str,
    *,
    expected_provider: str,
) -> SessionClaims:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "tid", "purpose", "p"]},
        )
    except jwt.PyJWTError as e:
        raise SessionInvalidError("invalid connector install ticket") from e
    if payload.get("purpose") != _CONNECTOR_INSTALL_PURPOSE:
        raise SessionInvalidError("invalid connector install ticket")
    if payload.get("p") != expected_provider:
        raise SessionInvalidError("connector install ticket provider mismatch")
    try:
        return SessionClaims(
            user_id=uuid.UUID(str(payload["sub"])),
            tenant_id=uuid.UUID(str(payload["tid"])),
        )
    except ValueError as e:
        raise SessionInvalidError("invalid connector install ticket") from e
