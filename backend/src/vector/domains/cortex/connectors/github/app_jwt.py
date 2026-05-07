"""JWT for GitHub App server-to-server API (installation metadata)."""

from __future__ import annotations

import time

import jwt

from vector.domains.cortex.connectors.github.errors import GitHubApiError
from vector.settings import Settings


def _jwt_issuer(settings: Settings) -> str:
    """GitHub expects `iss` to be the App's Client ID (Iv…), not the numeric App ID."""
    cid = settings.github_client_id.strip()
    if cid:
        return cid
    aid = settings.github_app_id.strip()
    if aid:
        return aid
    return ""


def create_github_app_jwt(settings: Settings) -> str:
    """Mint a short-lived JWT accepted by GitHub App APIs."""
    now = int(time.time())
    iss = _jwt_issuer(settings)
    if not iss:
        raise GitHubApiError("missing GITHUB_CLIENT_ID (or GITHUB_APP_ID) for JWT iss")
    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": iss,
    }
    try:
        return jwt.encode(
            payload,
            settings.github_app_private_key,
            algorithm="RS256",
        )
    except jwt.PyJWTError as e:
        raise GitHubApiError(
            "cannot sign GitHub App JWT — use full PEM with BEGIN/END lines (see logs)",
        ) from e
    except (TypeError, ValueError) as e:
        raise GitHubApiError("cannot sign GitHub App JWT — check GITHUB_APP_PRIVATE_KEY") from e
