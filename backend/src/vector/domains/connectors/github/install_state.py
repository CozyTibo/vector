"""Signed tenant + user binding for GitHub App install `state` query parameter."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from vector.domains.connectors.github.errors import InvalidGitHubInstallStateError
from vector.settings import Settings


@dataclass(frozen=True)
class GitHubInstallStateClaims:
    tenant_id: uuid.UUID
    user_id: uuid.UUID


def create_install_state_token(
    settings: Settings,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> str:
    ser = URLSafeTimedSerializer(settings.secret_key, salt="vector-github-install-state")
    return ser.dumps({"tid": str(tenant_id), "uid": str(user_id)})


def parse_install_state_token(
    settings: Settings,
    token: str,
    *,
    max_age_seconds: int = 900,
) -> GitHubInstallStateClaims:
    ser = URLSafeTimedSerializer(settings.secret_key, salt="vector-github-install-state")
    try:
        data = ser.loads(token, max_age=max_age_seconds)
    except SignatureExpired as e:
        raise InvalidGitHubInstallStateError("install state expired") from e
    except BadSignature as e:
        raise InvalidGitHubInstallStateError("invalid install state") from e
    tid_raw = data.get("tid")
    uid_raw = data.get("uid")
    if not tid_raw or not uid_raw:
        raise InvalidGitHubInstallStateError("invalid install state payload")
    try:
        return GitHubInstallStateClaims(
            tenant_id=uuid.UUID(str(tid_raw)),
            user_id=uuid.UUID(str(uid_raw)),
        )
    except ValueError as e:
        raise InvalidGitHubInstallStateError("invalid install state payload") from e
