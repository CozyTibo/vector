"""Signed tenant + user binding for Linear OAuth `state` parameter."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from vector.domains.connectors.linear.errors import InvalidLinearOAuthStateError
from vector.settings import Settings


@dataclass(frozen=True)
class LinearOAuthStateClaims:
    tenant_id: uuid.UUID
    user_id: uuid.UUID


def create_linear_oauth_state_token(
    settings: Settings,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> str:
    ser = URLSafeTimedSerializer(settings.secret_key, salt="vector-linear-oauth-state")
    return ser.dumps({"tid": str(tenant_id), "uid": str(user_id)})


def parse_linear_oauth_state_token(
    settings: Settings,
    token: str,
    *,
    max_age_seconds: int = 900,
) -> LinearOAuthStateClaims:
    ser = URLSafeTimedSerializer(settings.secret_key, salt="vector-linear-oauth-state")
    try:
        data = ser.loads(token, max_age=max_age_seconds)
    except SignatureExpired as e:
        raise InvalidLinearOAuthStateError("oauth state expired") from e
    except BadSignature as e:
        raise InvalidLinearOAuthStateError("invalid oauth state") from e
    tid_raw = data.get("tid")
    uid_raw = data.get("uid")
    if not tid_raw or not uid_raw:
        raise InvalidLinearOAuthStateError("invalid oauth state payload")
    try:
        return LinearOAuthStateClaims(
            tenant_id=uuid.UUID(str(tid_raw)),
            user_id=uuid.UUID(str(uid_raw)),
        )
    except ValueError as e:
        raise InvalidLinearOAuthStateError("invalid oauth state payload") from e
