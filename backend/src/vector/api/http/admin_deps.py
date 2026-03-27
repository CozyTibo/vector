"""HTTP Basic dependency for internal /admin APIs."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from vector.api.http.deps import settings_dep
from vector.settings import Settings

_admin_basic = HTTPBasic(auto_error=False)


def require_admin_basic(
    settings: Annotated[Settings, Depends(settings_dep)],
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_admin_basic)] = None,
) -> None:
    expected = (settings.admin_password or "").strip()
    if not expected:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API is disabled (set ADMIN_PASSWORD).",
        ) from None
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        ) from None
    if credentials.password != expected:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        ) from None
