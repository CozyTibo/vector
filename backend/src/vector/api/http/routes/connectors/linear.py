"""Linear OAuth (mounted at /connectors/linear)."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims, settings_dep
from vector.api.http.routes.connectors.install_response import install_redirect_or_json
from vector.application.services import connector_sync
from vector.contracts.connectors import (
    LinearIngestionRecordsPageResponse,
    LinearIngestionRunListItem,
    LinearIngestionRunsListResponse,
    LinearIngestionSyncResponse,
    LinearRawIngestionRecordItem,
)
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
from vector.domains.onboarding.connector_connected_chat_log import append_connector_connected_user_line
from vector.domains.ingestion.http_fetch import FetchFatalError
from vector.domains.ingestion.mock_preflight import preflight_mock_connectors_reachable
from vector.infrastructure.db.repositories import ingestion_queries as ing_queries
from vector.settings import Settings

_logger = logging.getLogger("app")


def build_linear_connector_router() -> APIRouter:
    r = APIRouter()

    @r.get("/install", response_model=None)
    def linear_oauth_start(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
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
        if settings.post_connect_enqueue_ingestion:
            try:
                preflight_mock_connectors_reachable(settings)
                connector_sync.enqueue_linear_poll_sync(db, tenant_id=_link.tenant_id)
            except Exception as exc:
                _logger.warning(
                    "post-connect Linear enqueue failed (POST /connectors/linear/sync): %s",
                    exc,
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

    @r.post(
        "/sync",
        response_model=LinearIngestionSyncResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def linear_graphql_sync(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> LinearIngestionSyncResponse:
        """Enqueue Linear GraphQL ingestion (Step 1–3 run on the Celery worker)."""
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        preflight_mock_connectors_reachable(settings)
        try:
            run = connector_sync.enqueue_linear_poll_sync(db, tenant_id=claims.tenant_id)
        except FetchFatalError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        db.commit()
        return LinearIngestionSyncResponse(
            run_id=run.id,
            status=run.status,
            error_summary=run.error_summary,
            stats=run.stats,
        )

    @r.get("/ingestion/runs", response_model=LinearIngestionRunsListResponse)
    def list_linear_ingestion_runs(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> LinearIngestionRunsListResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        runs = ing_queries.list_linear_ingestion_runs_for_tenant(
            db,
            claims.tenant_id,
            limit=limit,
        )
        counts = ing_queries.record_counts_for_run_ids(db, [r.id for r in runs])
        items = [
            LinearIngestionRunListItem(
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
        return LinearIngestionRunsListResponse(items=items)

    @r.get("/ingestion/runs/{run_id}/records", response_model=LinearIngestionRecordsPageResponse)
    def list_linear_ingestion_records(
        run_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> LinearIngestionRecordsPageResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        run = ing_queries.get_linear_ingestion_run_for_tenant(
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
            LinearRawIngestionRecordItem(
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
        return LinearIngestionRecordsPageResponse(
            run_id=run_id,
            total=page.total,
            limit=limit,
            offset=offset,
            items=rec_items,
        )

    return r
