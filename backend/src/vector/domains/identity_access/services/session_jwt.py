"""Signed session JWT for browser cookie."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from vector.domains.identity_access.errors import SessionInvalidError
from vector.settings import Settings


@dataclass(frozen=True)
class SessionClaims:
    user_id: uuid.UUID
    tenant_id: uuid.UUID


def issue_session_token(settings: Settings, user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    now = datetime.now(tz=UTC)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.session_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_session_token(settings: Settings, token: str) -> SessionClaims:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "tid"]},
        )
    except jwt.PyJWTError as e:
        raise SessionInvalidError("invalid session") from e
    try:
        return SessionClaims(
            user_id=uuid.UUID(str(payload["sub"])),
            tenant_id=uuid.UUID(str(payload["tid"])),
        )
    except ValueError as e:
        raise SessionInvalidError("invalid session claims") from e
