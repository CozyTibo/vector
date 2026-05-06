"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from vector.domains.identity_access.errors import SessionInvalidError
from vector.domains.identity_access.services.connector_install_ticket import decode_connector_install_ticket
from vector.domains.identity_access.services.session_jwt import SessionClaims, decode_session_token
from vector.infrastructure.db.session import db_session_dependency
from vector.settings import Settings, get_settings


def settings_dep() -> Settings:
    return get_settings()


def get_db() -> Generator[Session, None, None]:
    yield from db_session_dependency()


def _session_token_raw(request: Request, settings: Settings) -> str | None:
    raw = request.cookies.get(settings.session_cookie_name)
    if raw:
        return raw
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def get_session_claims(
    request: Request,
    settings: Annotated[Settings, Depends(settings_dep)],
) -> SessionClaims:
    raw = _session_token_raw(request, settings)
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return decode_session_token(settings, raw)
    except SessionInvalidError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated") from e


def resolve_connector_install_claims(
    request: Request,
    settings: Settings,
    provider: str,
    install_ticket: str | None,
) -> SessionClaims:
    """Cookie/Bearer session, or short-lived ``install_ticket`` for ``GET /connectors/.../install``."""
    raw = _session_token_raw(request, settings)
    if raw:
        try:
            return decode_session_token(settings, raw)
        except SessionInvalidError:
            pass
    if install_ticket:
        try:
            return decode_connector_install_ticket(
                settings, install_ticket, expected_provider=provider
            )
        except SessionInvalidError:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            ) from None
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def connector_install_claims_dependency(provider: str):
    def _dep(
        request: Request,
        settings: Annotated[Settings, Depends(settings_dep)],
        install_ticket: Annotated[str | None, Query()] = None,
    ) -> SessionClaims:
        return resolve_connector_install_claims(request, settings, provider, install_ticket)

    return _dep
