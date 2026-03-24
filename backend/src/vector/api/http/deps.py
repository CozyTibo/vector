"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from vector.domains.identity_access.errors import SessionInvalidError
from vector.domains.identity_access.services.session_jwt import SessionClaims, decode_session_token
from vector.infrastructure.db.session import db_session_dependency
from vector.settings import Settings, get_settings


def settings_dep() -> Settings:
    return get_settings()


def get_db() -> Generator[Session, None, None]:
    yield from db_session_dependency()


def get_session_claims(
    request: Request,
    settings: Annotated[Settings, Depends(settings_dep)],
) -> SessionClaims:
    raw = request.cookies.get(settings.session_cookie_name)
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return decode_session_token(settings, raw)
    except SessionInvalidError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated") from e
