"""GitHub App install + OAuth callback (mounted at /connectors/github)."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims, settings_dep
from vector.contracts.connectors import (
    GithubIngestionRecordsPageResponse,
    GithubIngestionRunListItem,
    GithubIngestionRunsListResponse,
    GithubIngestionSyncResponse,
    GithubRawIngestionRecordItem,
)
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
from vector.domains.ingestion.github_poll_sync import run_github_poll_ingestion_for_tenant
from vector.domains.ingestion.http_fetch import FetchFatalError
from vector.domains.projections.github.worker import drain_github_projections
from vector.infrastructure.db.repositories import ingestion_queries as ing_queries
from vector.infrastructure.db.repositories.ingestion import RUN_STATUS_SUCCEEDED
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

    @r.post("/sync", response_model=GithubIngestionSyncResponse)
    def github_poll_sync(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> GithubIngestionSyncResponse:
        """Poll GitHub REST and append resource-level raw ingestion rows (Step 1)."""
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        try:
            run = run_github_poll_ingestion_for_tenant(db, settings, claims.tenant_id)
        except FetchFatalError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        if run.status == RUN_STATUS_SUCCEEDED:
            drain_github_projections(
                db,
                tenant_id=claims.tenant_id,
                connection_id=run.connection_id,
            )
        return GithubIngestionSyncResponse(
            run_id=run.id,
            status=run.status,
            error_summary=run.error_summary,
            stats=run.stats,
        )

    @r.get("/ingestion/runs", response_model=GithubIngestionRunsListResponse)
    def list_github_ingestion_runs(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> GithubIngestionRunsListResponse:
        """List GitHub ingestion runs for this tenant (newest first)."""
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        runs = ing_queries.list_github_ingestion_runs_for_tenant(
            db,
            claims.tenant_id,
            limit=limit,
        )
        counts = ing_queries.record_counts_for_run_ids(db, [r.id for r in runs])
        items = [
            GithubIngestionRunListItem(
                id=run.id,
                connection_id=run.connection_id,
                status=run.status,
                source_trigger=run.source_trigger,
                started_at=run.started_at,
                finished_at=run.finished_at,
                error_summary=run.error_summary,
                stats=run.stats,
                records_written=counts.get(run.id, 0),
            )
            for run in runs
        ]
        return GithubIngestionRunsListResponse(items=items)

    @r.get("/ingestion/runs/{run_id}/records", response_model=GithubIngestionRecordsPageResponse)
    def list_github_ingestion_records(
        run_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> GithubIngestionRecordsPageResponse:
        """Paginated raw ingestion rows for one run (replay order)."""
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        run = ing_queries.get_github_ingestion_run_for_tenant(
            db,
            tenant_id=claims.tenant_id,
            run_id=run_id,
        )
        if run is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Ingestion run not found.",
            ) from None
        page = ing_queries.list_raw_records_for_run(
            db,
            run_id=run_id,
            limit=limit,
            offset=offset,
        )
        rec_items = [
            GithubRawIngestionRecordItem(
                id=rec.id,
                replay_sequence=rec.replay_sequence,
                resource_type=rec.resource_type,
                external_id=rec.external_id,
                api_endpoint=rec.api_endpoint,
                query_params=dict(rec.query_params) if rec.query_params is not None else {},
                payload_hash=rec.payload_hash,
                http_status=rec.http_status,
                fetched_at=rec.fetched_at,
                payload_body=dict(rec.payload_body) if rec.payload_body is not None else {},
            )
            for rec in page.items
        ]
        return GithubIngestionRecordsPageResponse(
            run_id=run_id,
            total=page.total,
            limit=limit,
            offset=offset,
            items=rec_items,
        )

    return r
