"""Set session cookie on responses (API + OAuth callback)."""

from __future__ import annotations

import os

from starlette.requests import Request
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


def request_indicates_https(request: Request | None) -> bool:
    """True when the inbound request is HTTPS (direct TLS or behind TLS-terminating proxy)."""
    if request is None:
        return False
    forwarded = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    if forwarded == "https":
        return True
    return request.url.scheme == "https"


def _effective_cross_site(settings: Settings, request: Request | None) -> bool:
    """
    SameSite=None + Secure must not be emitted over plain HTTP: mobile and desktop
    browsers will drop the Set-Cookie, so login/register appear to succeed in the DB
    but ``/me`` stays anonymous.
    """
    cross = session_cookie_cross_site(settings)
    if not cross:
        return False
    if not request_indicates_https(request):
        return False
    return True


def set_session_cookie(
    response: Response,
    settings: Settings,
    token: str,
    *,
    request: Request | None = None,
) -> None:
    cross = _effective_cross_site(settings, request)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=cross,
        samesite="none" if cross else "lax",
        max_age=settings.session_ttl_seconds,
        path="/",
    )


def clear_session_cookie(
    response: Response,
    settings: Settings,
    *,
    request: Request | None = None,
) -> None:
    """Clear session cookie with attributes matching :func:`set_session_cookie`."""
    cross = _effective_cross_site(settings, request)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=cross,
        httponly=True,
        samesite="none" if cross else "lax",
    )
