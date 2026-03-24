"""GitHub App install + OAuth callback (mounted at /connectors/github)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims, settings_dep
from vector.domains.connectors.github.errors import (
    GitHubApiError,
    GitHubConnectorNotConfiguredError,
    GitHubInstallationConflictError,
    GitHubInstallMissingError,
    GitHubInstallStateMembershipError,
    GitHubUserOAuthError,
    InvalidGitHubInstallStateError,
)
from vector.domains.connectors.github.install_flow import (
    complete_github_install,
    start_github_install_url,
)
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import assert_membership
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.settings import Settings

_logger = logging.getLogger(__name__)


def build_github_connector_router() -> APIRouter:
    r = APIRouter()

    @r.get("/install")
    def github_install_start(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> RedirectResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        try:
            url = start_github_install_url(settings, claims.tenant_id, claims.user_id)
        except GitHubConnectorNotConfiguredError as e:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)

    @r.get("/callback")
    def github_install_callback(
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
        code: str,
        state: str,
        installation_id: int | None = None,
    ) -> RedirectResponse:
        """OAuth return from GitHub (session optional; signed `state` carries tenant + user)."""
        front = settings.frontend_url.rstrip("/")
        try:
            complete_github_install(
                db,
                settings,
                code=code,
                state=state,
                installation_id=installation_id,
            )
        except GitHubInstallStateMembershipError:
            return RedirectResponse(
                url=f"{front}/?github_error=forbidden",
                status_code=status.HTTP_302_FOUND,
            )
        except InvalidGitHubInstallStateError:
            return RedirectResponse(
                url=f"{front}/?github_error=state",
                status_code=status.HTTP_302_FOUND,
            )
        except GitHubInstallMissingError:
            return RedirectResponse(
                url=f"{front}/?github_error=no_installation",
                status_code=status.HTTP_302_FOUND,
            )
        except GitHubUserOAuthError:
            return RedirectResponse(
                url=f"{front}/?github_error=oauth",
                status_code=status.HTTP_302_FOUND,
            )
        except GitHubApiError as exc:
            _logger.warning("GitHub installation API failed: %s", exc)
            return RedirectResponse(
                url=f"{front}/?github_error=api",
                status_code=status.HTTP_302_FOUND,
            )
        except GitHubInstallationConflictError:
            return RedirectResponse(
                url=f"{front}/?github_error=conflict",
                status_code=status.HTTP_302_FOUND,
            )
        except GitHubConnectorNotConfiguredError:
            return RedirectResponse(
                url=f"{front}/?github_error=config",
                status_code=status.HTTP_302_FOUND,
            )
        except Exception:
            _logger.exception("GitHub install callback failed")
            return RedirectResponse(
                url=f"{front}/?github_error=server",
                status_code=status.HTTP_302_FOUND,
            )
        return RedirectResponse(
            url=f"{front}/?github_connected=1",
            status_code=status.HTTP_302_FOUND,
        )

    return r
