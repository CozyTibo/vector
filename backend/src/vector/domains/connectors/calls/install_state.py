"""Signed tenant + user binding for Calls OAuth `state` parameter."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from vector.domains.connectors.calls.errors import InvalidCallsOAuthStateError
from vector.domains.connectors.github.return_path import sanitize_github_install_return_to
from vector.settings import Settings


@dataclass(frozen=True)
class CallsOAuthStateClaims:
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    return_to: str | None = None


def create_calls_oauth_state_token(
    settings: Settings,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    return_to: str | None = None,
) -> str:
    ser = URLSafeTimedSerializer(settings.secret_key, salt="vector-calls-oauth-state")
    payload: dict[str, str] = {"tid": str(tenant_id), "uid": str(user_id)}
    safe = sanitize_github_install_return_to(return_to)
    if safe:
        payload["next"] = safe
    return ser.dumps(payload)


def parse_calls_oauth_state_token(
    settings: Settings,
    token: str,
    *,
    max_age_seconds: int = 900,
) -> CallsOAuthStateClaims:
    ser = URLSafeTimedSerializer(settings.secret_key, salt="vector-calls-oauth-state")
    try:
        data = ser.loads(token, max_age=max_age_seconds)
    except SignatureExpired as e:
        raise InvalidCallsOAuthStateError("oauth state expired") from e
    except BadSignature as e:
        raise InvalidCallsOAuthStateError("invalid oauth state") from e
    tid_raw = data.get("tid")
    uid_raw = data.get("uid")
    if not tid_raw or not uid_raw:
        raise InvalidCallsOAuthStateError("invalid oauth state payload")
    next_raw = data.get("next")
    safe_next: str | None = None
    if isinstance(next_raw, str):
        safe_next = sanitize_github_install_return_to(next_raw)
    try:
        return CallsOAuthStateClaims(
            tenant_id=uuid.UUID(str(tid_raw)),
            user_id=uuid.UUID(str(uid_raw)),
            return_to=safe_next,
        )
    except ValueError as e:
        raise InvalidCallsOAuthStateError("invalid oauth state payload") from e
