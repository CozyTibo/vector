"""Notion OAuth (mounted at /connectors/notion)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims, settings_dep
from vector.domains.connectors.notion.errors import (
    InvalidNotionOAuthStateError,
    NotionConnectorNotConfiguredError,
    NotionInstallStateMembershipError,
    NotionOAuthError,
)
from vector.domains.connectors.notion.oauth_flow import complete_notion_oauth, start_notion_oauth_url
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import assert_membership
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.domains.onboarding.connector_connected_chat_log import append_connector_connected_user_line
from vector.settings import Settings

_logger = logging.getLogger("app")


def build_notion_connector_router() -> APIRouter:
    r = APIRouter()

    @r.get("/install")
    def notion_oauth_start(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        settings: Annotated[Settings, Depends(settings_dep)],
        return_to: Annotated[str | None, Query(description="Post-OAuth redirect path")] = None,
    ) -> RedirectResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        try:
            url = start_notion_oauth_url(
                settings,
                claims.tenant_id,
                claims.user_id,
                return_to=return_to,
            )
        except NotionConnectorNotConfiguredError as e:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)

    @r.get("/callback")
    def notion_oauth_callback(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
        code: str,
        state: str,
    ) -> RedirectResponse:
        front = settings.frontend_url.rstrip("/")
        return_to: str | None = None
        try:
            link, return_to = complete_notion_oauth(db, settings, code=code, state=state)
        except NotionInstallStateMembershipError:
            return RedirectResponse(url=f"{front}/?notion_error=forbidden", status_code=status.HTTP_302_FOUND)
        except InvalidNotionOAuthStateError:
            return RedirectResponse(url=f"{front}/?notion_error=state", status_code=status.HTTP_302_FOUND)
        except NotionOAuthError as exc:
            _logger.warning("Notion OAuth failed: %s", exc)
            return RedirectResponse(url=f"{front}/?notion_error=oauth", status_code=status.HTTP_302_FOUND)
        except NotionConnectorNotConfiguredError:
            return RedirectResponse(url=f"{front}/?notion_error=config", status_code=status.HTTP_302_FOUND)
        except Exception:
            _logger.exception("Notion OAuth callback failed")
            return RedirectResponse(url=f"{front}/?notion_error=server", status_code=status.HTTP_302_FOUND)
        append_connector_connected_user_line(
            db,
            tenant_id=link.connection.tenant_id,
            user_id=link.connection.connected_by_user_id,
            return_to=return_to,
            tool_label="Notion",
        )
        ok = f"{front}{return_to}?notion_connected=1" if return_to else f"{front}/?notion_connected=1"
        return RedirectResponse(url=ok, status_code=status.HTTP_302_FOUND)

    return r
