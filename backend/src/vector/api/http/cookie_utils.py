"""Set session cookie on responses (API + OAuth callback)."""

from __future__ import annotations

import os

from starlette.responses import Response

from vector.settings import Settings


def session_cookie_cross_site(settings: Settings) -> bool:
    """
    When the SPA is on a different site than the API (e.g. CloudFront vs api.*),
    browsers require ``SameSite=None; Secure`` or credentialed ``fetch`` will not
    send the session cookie on ``/me`` and other API calls.

    Override with ``SESSION_COOKIE_CROSS_SITE=true|false`` if needed (e.g. same-site
    subdomains only: ``app`` + ``api`` under the same registrable domain can use Lax).
    """
    raw = os.environ.get("SESSION_COOKIE_CROSS_SITE", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    return settings.env in ("production", "staging")


def set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    cross = session_cookie_cross_site(settings)
    # SameSite=None is ignored unless Secure is true (HTTPS).
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=cross,
        samesite="none" if cross else "lax",
        max_age=settings.session_ttl_seconds,
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    """Clear session cookie with attributes matching :func:`set_session_cookie`."""
    cross = session_cookie_cross_site(settings)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=cross,
        httponly=True,
        samesite="none" if cross else "lax",
    )
