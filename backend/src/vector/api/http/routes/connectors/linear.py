"""Linear OAuth (mounted at /connectors/linear)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims, settings_dep
from vector.domains.connectors.linear.errors import (
    InvalidLinearOAuthStateError,
    LinearConnectorNotConfiguredError,
    LinearInstallStateMembershipError,
    LinearOAuthError,
)
from vector.domains.connectors.linear.oauth_flow import (
    complete_linear_oauth,
    start_linear_oauth_url,
)
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import assert_membership
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.settings import Settings

_logger = logging.getLogger(__name__)


def build_linear_connector_router() -> APIRouter:
    r = APIRouter()

    @r.get("/install")
    def linear_oauth_start(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> RedirectResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        try:
            url = start_linear_oauth_url(settings, claims.tenant_id, claims.user_id)
        except LinearConnectorNotConfiguredError as e:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)

    @r.get("/callback")
    def linear_oauth_callback(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
        code: str,
        state: str,
    ) -> RedirectResponse:
        """OAuth return from Linear (session optional; `state` binds tenant + user)."""
        front = settings.frontend_url.rstrip("/")
        try:
            complete_linear_oauth(db, settings, code=code, state=state)
        except LinearInstallStateMembershipError:
            return RedirectResponse(
                url=f"{front}/?linear_error=forbidden",
                status_code=status.HTTP_302_FOUND,
            )
        except InvalidLinearOAuthStateError:
            return RedirectResponse(
                url=f"{front}/?linear_error=state",
                status_code=status.HTTP_302_FOUND,
            )
        except LinearOAuthError as exc:
            _logger.warning("Linear OAuth failed: %s", exc)
            return RedirectResponse(
                url=f"{front}/?linear_error=oauth",
                status_code=status.HTTP_302_FOUND,
            )
        except LinearConnectorNotConfiguredError:
            return RedirectResponse(
                url=f"{front}/?linear_error=config",
                status_code=status.HTTP_302_FOUND,
            )
        except Exception:
            _logger.exception("Linear OAuth callback failed")
            return RedirectResponse(
                url=f"{front}/?linear_error=server",
                status_code=status.HTTP_302_FOUND,
            )
        return RedirectResponse(
            url=f"{front}/?linear_connected=1",
            status_code=status.HTTP_302_FOUND,
        )

    return r
