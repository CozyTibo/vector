"""Slack OAuth: install under /connectors/slack; callback at /slack/callback (matches SLACK_CALLBACK_URL)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
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
from vector.infrastructure.db.models.slack_bot_message import SlackBotMessage
from vector.infrastructure.db.models.slack_user_tenant_map import SlackUserTenantMap
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

    @r.post("/slack/events")
    async def slack_events(
        request: Request,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> JSONResponse:
        raw_body = await request.body()
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            return JSONResponse({"ok": True})

        if body.get("type") == "url_verification":
            return JSONResponse({"challenge": body["challenge"]})

        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        slack_sig = request.headers.get("X-Slack-Signature", "")
        signing_secret = settings.slack_signing_secret.strip()
        if not signing_secret:
            raise HTTPException(status_code=403, detail="Slack signing secret not configured")
        try:
            if abs(time.time() - float(timestamp)) > 60 * 5:
                raise HTTPException(status_code=403, detail="Stale timestamp")
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=403, detail="Invalid timestamp") from exc

        sig_basestring = f"v0:{timestamp}:{raw_body.decode()}"
        computed = (
            "v0="
            + hmac.new(
                signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )
        if not hmac.compare_digest(computed, slack_sig):
            raise HTTPException(status_code=403, detail="Invalid signature")

        try:
            payload = body
            event = payload.get("event", {})
            if payload.get("type") != "event_callback":
                return JSONResponse({"ok": True})
            if event.get("type") != "message":
                return JSONResponse({"ok": True})
            if event.get("channel_type") != "im":
                return JSONResponse({"ok": True})
            if event.get("bot_id"):
                return JSONResponse({"ok": True})
            if event.get("subtype"):
                return JSONResponse({"ok": True})

            team_id = payload.get("team_id")
            slack_user_id = event.get("user")
            if not isinstance(team_id, str) or not isinstance(slack_user_id, str):
                return JSONResponse({"ok": True})

            mapping = db.scalars(
                select(SlackUserTenantMap).where(
                    SlackUserTenantMap.slack_team_id == team_id,
                    SlackUserTenantMap.slack_user_id == slack_user_id,
                )
            ).first()
            if mapping is None:
                _logger.warning(
                    "No tenant mapping for team=%s user=%s",
                    team_id,
                    slack_user_id,
                )
                return JSONResponse({"ok": True})

            slack_event_id = event.get("event_ts") or event.get("ts")
            if isinstance(slack_event_id, str) and slack_event_id.strip():
                existing = db.scalars(
                    select(SlackBotMessage).where(
                        SlackBotMessage.slack_event_id == slack_event_id,
                    )
                ).first()
                if existing is not None:
                    return JSONResponse({"ok": True})

            channel = event.get("channel")
            ts = event.get("ts")
            if not isinstance(channel, str) or not isinstance(ts, str):
                return JSONResponse({"ok": True})

            db.add(
                SlackBotMessage(
                    tenant_id=mapping.tenant_id,
                    slack_team_id=team_id,
                    slack_user_id=slack_user_id,
                    slack_channel_id=channel,
                    slack_ts=ts,
                    direction="inbound",
                    text=str(event.get("text", "")),
                    slack_event_id=slack_event_id if isinstance(slack_event_id, str) else None,
                )
            )
            db.commit()
        except Exception:
            _logger.exception("Slack events processing failed")
        return JSONResponse({"ok": True})

    return r
