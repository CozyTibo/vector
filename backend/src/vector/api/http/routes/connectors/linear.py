"""Linear OAuth (mounted at /connectors/linear)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import (
    connector_install_claims_dependency,
    get_db,
    get_session_claims,
    settings_dep,
)
from vector.api.http.routes.connectors.install_response import install_redirect_or_json
from vector.domains.cortex.connectors.linear.errors import (
    InvalidLinearOAuthStateError,
    LinearConnectorNotConfiguredError,
    LinearInstallStateMembershipError,
    LinearOAuthError,
)
from vector.domains.cortex.connectors.linear.oauth_flow import (
    complete_linear_oauth,
    start_linear_oauth_url,
)
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import assert_membership
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.domains.onboarding.connector_connected_chat_log import append_connector_connected_user_line
from vector.settings import Settings

_logger = logging.getLogger("app")


def build_linear_connector_router() -> APIRouter:
    r = APIRouter()

    @r.get("/install", response_model=None)
    def linear_oauth_start(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(connector_install_claims_dependency("linear"))],
        settings: Annotated[Settings, Depends(settings_dep)],
        return_to: Annotated[str | None, Query(description="Post-OAuth redirect path")] = None,
        install_response: Annotated[
            str | None,
            Query(
                description=(
                    "When ``json``, return ``{\"url\": ...}`` instead of HTTP redirect "
                    "(used by SPA fetch with Authorization)."
                ),
            ),
        ] = None,
    ) -> RedirectResponse | JSONResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        try:
            url = start_linear_oauth_url(
                settings,
                claims.tenant_id,
                claims.user_id,
                return_to=return_to,
            )
        except LinearConnectorNotConfiguredError as e:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
        return install_redirect_or_json(url, install_response=install_response)

    @r.get("/callback")
    def linear_oauth_callback(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
        code: str,
        state: str,
    ) -> RedirectResponse:
        """OAuth return from Linear (session optional; `state` binds tenant + user)."""
        front = settings.frontend_url.rstrip("/")
        return_to: str | None = None
        try:
            _link, return_to = complete_linear_oauth(db, settings, code=code, state=state)
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
        append_connector_connected_user_line(
            db,
            tenant_id=_link.tenant_id,
            user_id=_link.connection.connected_by_user_id,
            return_to=return_to,
            tool_label="Linear",
        )
        ok = (
            f"{front}{return_to}?linear_connected=1"
            if return_to
            else f"{front}/?linear_connected=1"
        )
        return RedirectResponse(url=ok, status_code=status.HTTP_302_FOUND)

    return r
