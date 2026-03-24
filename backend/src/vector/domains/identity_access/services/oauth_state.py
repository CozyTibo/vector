"""Signed OAuth state cookie (PKCE verifier + random state)."""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from vector.domains.identity_access.errors import InvalidOAuthStateError
from vector.settings import Settings


@dataclass(frozen=True)
class OAuthStatePayload:
    state: str
    code_verifier: str


def create_oauth_state(settings: Settings) -> OAuthStatePayload:
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    return OAuthStatePayload(state=state, code_verifier=verifier)


def code_challenge_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def serialize_oauth_cookie(settings: Settings, payload: OAuthStatePayload) -> str:
    ser = URLSafeTimedSerializer(settings.secret_key, salt="vector-oauth-state")
    return ser.dumps({"s": payload.state, "v": payload.code_verifier})


def parse_oauth_cookie(
    settings: Settings,
    cookie_value: str,
    max_age: int = 600,
) -> OAuthStatePayload:
    ser = URLSafeTimedSerializer(settings.secret_key, salt="vector-oauth-state")
    try:
        data = ser.loads(cookie_value, max_age=max_age)
    except SignatureExpired as e:
        raise InvalidOAuthStateError("oauth state expired") from e
    except BadSignature as e:
        raise InvalidOAuthStateError("invalid oauth state") from e
    state = str(data["s"])
    verifier = str(data["v"])
    if not state or not verifier:
        raise InvalidOAuthStateError("invalid oauth state payload")
    return OAuthStatePayload(state=state, code_verifier=verifier)
