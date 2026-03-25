"""Debug UI: inspect connector projection tables (engineers only)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims
from vector.api.http.serialization import orm_to_dict
from vector.contracts.debug_projections import (
    ProjectionRowsResponse,
    RawIngestionRecordDebugItem,
    RawIngestionRecordDebugResponse,
)
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import assert_membership
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.infrastructure.db.repositories import projection_debug_queries as dbg

GITHUB_ENTITIES = frozenset(
    {
        "repositories",
        "pull_requests",
        "issues",
        "commits",
        "users",
    },
)


def build_debug_projections_router() -> APIRouter:
    r = APIRouter()

    @r.get(
        "/connectors/{connector}/connections/{connection_id}/projections/rows",
        response_model=ProjectionRowsResponse,
    )
    def list_projection_rows(
        connector: str,
        connection_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        entity: Annotated[str, Query(description="repositories | pull_requests | …")],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        q: Annotated[str | None, Query(description="Filter substring")] = None,
    ) -> ProjectionRowsResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        if connector != "github":
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Unsupported connector for projections debug.",
            ) from None
        if entity not in GITHUB_ENTITIES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown entity '{entity}'.",
            ) from None
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=claims.tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Connection not found for tenant.",
            ) from None

        listers: dict[str, Any] = {
            "repositories": dbg.list_github_repositories,
            "pull_requests": dbg.list_github_pull_requests,
            "issues": dbg.list_github_issues,
            "commits": dbg.list_github_commits,
            "users": dbg.list_github_users,
        }
        page = listers[entity](
            db,
            tenant_id=claims.tenant_id,
            connection_id=connection_id,
            limit=limit,
            offset=offset,
            q=q,
        )

        items = [orm_to_dict(row) for row in page.items]
        return ProjectionRowsResponse(
            connector=connector,
            connection_id=connection_id,
            entity=entity,
            total=page.total,
            limit=limit,
            offset=offset,
            items=items,
        )

    @r.get(
        "/connectors/{connector}/connections/{connection_id}/raw-records/{record_id}",
        response_model=RawIngestionRecordDebugResponse,
    )
    def get_raw_record(
        connector: str,
        connection_id: uuid.UUID,
        record_id: int,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> RawIngestionRecordDebugResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        if connector != "github":
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Unsupported connector.",
            ) from None
        raw = dbg.get_raw_record_for_tenant(db, tenant_id=claims.tenant_id, record_id=record_id)
        if raw is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Raw record not found.") from None
        if raw.connection_id != connection_id:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Raw record does not belong to this connection.",
            ) from None
        body = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
        return RawIngestionRecordDebugResponse(
            item=RawIngestionRecordDebugItem(
                id=raw.id,
                replay_sequence=raw.replay_sequence,
                connection_id=raw.connection_id,
                connector=raw.connector,
                resource_type=raw.resource_type,
                external_id=raw.external_id,
                http_status=raw.http_status,
                fetched_at=raw.fetched_at.isoformat(),
                run_id=raw.run_id,
                payload_body=body,
            ),
        )

    return r
