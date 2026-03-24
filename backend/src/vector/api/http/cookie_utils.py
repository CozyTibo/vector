"""Set session cookie on responses (API + OAuth callback)."""

from __future__ import annotations

from starlette.responses import Response

from vector.settings import Settings


def set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
