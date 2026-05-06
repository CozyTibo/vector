"""Helpers for /connectors/*/install: HTTP redirect vs JSON for SPA OAuth bootstrap."""

from __future__ import annotations

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse


def install_redirect_or_json(
    url: str,
    *,
    install_response: str | None,
) -> RedirectResponse | JSONResponse:
    """Return 302 to OAuth URL, or 200 JSON ``{\"url\": ...}`` when ``install_response=json``."""
    if install_response in (None, ""):
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    if install_response == "json":
        return JSONResponse({"url": url})
    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        detail="install_response must be 'json' or omitted.",
    ) from None
