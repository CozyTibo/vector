"""Slack OAuth: install under /connectors/slack; callback at /slack/callback (matches SLACK_CALLBACK_URL)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import connector_install_claims_dependency, get_db, settings_dep
from vector.api.http.routes.connectors.install_response import install_redirect_or_json
from vector.domains.cortex.connectors.slack.errors import (
    InvalidSlackOAuthStateError,
    SlackConnectorNotConfiguredError,
    SlackInstallStateMembershipError,
    SlackOAuthError,
    SlackWorkspaceConflictError,
)
from vector.domains.cortex.connectors.slack.oauth_flow import (
    complete_slack_oauth,
    slack_oauth_error_frontend_redirect_url,
    start_slack_oauth_url,
)
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import assert_membership
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.domains.onboarding.connector_connected_chat_log import append_connector_connected_user_line
from vector.settings import Settings

_logger = logging.getLogger("app")


def build_slack_connector_router() -> APIRouter:
    r = APIRouter()

    @r.get("/install", response_model=None)
    def slack_oauth_start(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(connector_install_claims_dependency("slack"))],
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
            url = start_slack_oauth_url(
                settings,
                claims.tenant_id,
                claims.user_id,
                return_to=return_to,
            )
        except SlackConnectorNotConfiguredError:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Slack OAuth is not configured: set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET in the "
                    "API environment. With Docker Compose, add them to the repo root `.env` and "
                    "recreate the backend container (`docker compose up -d --force-recreate backend`) "
                    "so variables load from `env_file`."
                ),
            ) from None
        return install_redirect_or_json(url, install_response=install_response)

    return r


def build_slack_callback_router() -> APIRouter:
    """Mounted at app root so `SLACK_CALLBACK_URL` can be `https://host/slack/callback`."""

    r = APIRouter(tags=["connectors"])

    @r.get("/slack/callback")
    def slack_oauth_callback(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
        code: Annotated[str | None, Query()] = None,
        state: Annotated[str | None, Query()] = None,
        error: Annotated[str | None, Query()] = None,
        error_description: Annotated[str | None, Query()] = None,
    ) -> RedirectResponse:
        """OAuth return from Slack (session optional; `state` binds tenant + user).

        Slack may redirect with ``error`` / ``error_description`` (e.g. ``access_denied``) instead of
        ``code`` when the user cancels or the app rejects the workspace.
        """
        front = settings.frontend_url.rstrip("/")
        if error:
            _logger.info(
                "Slack OAuth redirect error: %s (%s)",
                error,
                (error_description or "").replace("\n", " ")[:500],
            )
            err_q = "denied" if error == "access_denied" else "oauth"
            return RedirectResponse(
                url=slack_oauth_error_frontend_redirect_url(settings, state, err_q),
                status_code=status.HTTP_302_FOUND,
            )
        if not code or not state:
            _logger.warning("Slack callback missing code or state")
            return RedirectResponse(
                url=slack_oauth_error_frontend_redirect_url(settings, state, "oauth"),
                status_code=status.HTTP_302_FOUND,
            )
        return_to: str | None = None
        try:
            _link, return_to = complete_slack_oauth(db, settings, code=code, state=state)
        except SlackInstallStateMembershipError:
            return RedirectResponse(
                url=slack_oauth_error_frontend_redirect_url(settings, state, "forbidden"),
                status_code=status.HTTP_302_FOUND,
            )
        except InvalidSlackOAuthStateError:
            return RedirectResponse(
                url=slack_oauth_error_frontend_redirect_url(settings, state, "state"),
                status_code=status.HTTP_302_FOUND,
            )
        except SlackOAuthError as exc:
            _logger.warning("Slack OAuth failed: %s", exc)
            return RedirectResponse(
                url=slack_oauth_error_frontend_redirect_url(settings, state, "oauth"),
                status_code=status.HTTP_302_FOUND,
            )
        except SlackConnectorNotConfiguredError:
            return RedirectResponse(
                url=slack_oauth_error_frontend_redirect_url(settings, state, "config"),
                status_code=status.HTTP_302_FOUND,
            )
        except SlackWorkspaceConflictError:
            return RedirectResponse(
                url=slack_oauth_error_frontend_redirect_url(settings, state, "workspace_taken"),
                status_code=status.HTTP_302_FOUND,
            )
        except Exception:
            _logger.exception("Slack OAuth callback failed")
            return RedirectResponse(
                url=slack_oauth_error_frontend_redirect_url(settings, state, "server"),
                status_code=status.HTTP_302_FOUND,
            )
        append_connector_connected_user_line(
            db,
            tenant_id=_link.connection.tenant_id,
            user_id=_link.connection.connected_by_user_id,
            return_to=return_to,
            tool_label="Slack",
        )
        ok = (
            f"{front}{return_to}?slack_connected=1"
            if return_to
            else f"{front}/?slack_connected=1"
        )
        _logger.info("Slack OAuth completed; redirecting to frontend with slack_connected=1")
        return RedirectResponse(url=ok, status_code=status.HTTP_302_FOUND)

    return r
