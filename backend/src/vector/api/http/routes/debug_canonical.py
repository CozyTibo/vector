"""Debug UI: canonical ontology (Step 3)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims, settings_dep
from vector.api.http.serialization import orm_to_dict
from vector.contracts.debug_canonical import (
    CanonicalStatusResponse,
    PaginatedResponse,
    SubgraphAnchor,
    SubgraphEdge,
    SubgraphNode,
    SubgraphResponse,
)
from vector.domains.canonical.worker import (
    count_canonical_lag,
    drain_github_canonical,
    drain_linear_canonical,
)
from vector.domains.debug.github_pipeline_wipe import (
    rebuild_derived_from_step1_github,
    reset_github_pipeline_state,
)
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import assert_membership
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.domains.ingestion.github_poll_sync import run_github_poll_ingestion_for_tenant
from vector.domains.projections.github.worker import drain_github_projections
from vector.infrastructure.db.models.canonical import Step3CanonicalCursor
from vector.infrastructure.db.repositories import canonical_debug_queries as cq
from vector.infrastructure.db.repositories import projection_debug_queries as dbg
from vector.infrastructure.db.repositories.ingestion import (
    CONNECTOR_GITHUB,
    CONNECTOR_LINEAR,
    RUN_STATUS_SUCCEEDED,
)


def build_debug_canonical_router() -> APIRouter:
    r = APIRouter()

    @r.get("/canonical/actors", response_model=PaginatedResponse)
    def list_actors(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        q: Annotated[str | None, Query()] = None,
    ) -> PaginatedResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        page = cq.list_actors(db, tenant_id=claims.tenant_id, limit=limit, offset=offset, q=q)
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/canonical/artifacts", response_model=PaginatedResponse)
    def list_artifacts(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        artifact_kind_id: Annotated[int | None, Query()] = None,
        q: Annotated[str | None, Query()] = None,
    ) -> PaginatedResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        page = cq.list_artifacts(
            db,
            tenant_id=claims.tenant_id,
            artifact_kind_id=artifact_kind_id,
            limit=limit,
            offset=offset,
            q=q,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/canonical/relationships", response_model=PaginatedResponse)
    def list_relationships(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        current_only: Annotated[bool, Query()] = True,
    ) -> PaginatedResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        page = cq.list_relationships(
            db,
            tenant_id=claims.tenant_id,
            current_only=current_only,
            limit=limit,
            offset=offset,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/canonical/external-references", response_model=PaginatedResponse)
    def list_external_references(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> PaginatedResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        page = cq.list_external_references(
            db,
            tenant_id=claims.tenant_id,
            limit=limit,
            offset=offset,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/canonical/mapping-events", response_model=PaginatedResponse)
    def list_mapping_events(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        external_reference_id: Annotated[uuid.UUID | None, Query()] = None,
    ) -> PaginatedResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        page = cq.list_mapping_events(
            db,
            tenant_id=claims.tenant_id,
            external_reference_id=external_reference_id,
            limit=limit,
            offset=offset,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/canonical/actors/{actor_id}")
    def get_actor(
        actor_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> dict[str, Any]:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        detail = cq.actor_detail(db, tenant_id=claims.tenant_id, actor_id=actor_id)
        if detail is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Actor not found.") from None
        return detail

    @r.get("/canonical/artifacts/{artifact_id}")
    def get_artifact(
        artifact_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> dict[str, Any]:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        detail = cq.artifact_detail(db, tenant_id=claims.tenant_id, artifact_id=artifact_id)
        if detail is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artifact not found.") from None
        return detail

    @r.get("/canonical/relationships/{relationship_id}")
    def get_relationship(
        relationship_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> dict[str, Any]:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        detail = cq.relationship_detail(
            db,
            tenant_id=claims.tenant_id,
            relationship_id=relationship_id,
        )
        if detail is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Relationship not found.",
            ) from None
        return detail

    @r.get("/canonical/external-references/{xref_id}")
    def get_external_reference(
        xref_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> dict[str, Any]:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        detail = cq.external_reference_detail(db, tenant_id=claims.tenant_id, xref_id=xref_id)
        if detail is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="External reference not found.",
            ) from None
        return detail

    @r.get("/canonical/status", response_model=CanonicalStatusResponse)
    def canonical_status(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        connection_id: Annotated[uuid.UUID, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> CanonicalStatusResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=claims.tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None
        lag, meta = count_canonical_lag(
            db,
            tenant_id=claims.tenant_id,
            connection_id=connection_id,
            connector=connector,
        )
        cursor_row = db.get(Step3CanonicalCursor, (connection_id, connector))
        ts = cursor_row.last_processed_at if cursor_row else None
        return CanonicalStatusResponse(
            tenant_id=claims.tenant_id,
            connection_id=connection_id,
            connector=connector,
            step3_last_processed_replay_sequence=int(meta["step3_last_processed_replay_sequence"]),
            step3_last_processed_id=int(meta["step3_last_processed_id"]),
            step3_lag_rows=lag,
            step3_last_processed_timestamp=ts,
            step2_watermark_replay_sequence=int(meta["step2_watermark_replay_sequence"]),
            step2_watermark_id=int(meta["step2_watermark_id"]),
        )

    @r.get("/canonical/subgraph", response_model=SubgraphResponse)
    def subgraph(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        artifact_id: Annotated[uuid.UUID | None, Query()] = None,
        actor_id: Annotated[uuid.UUID | None, Query()] = None,
        depth: Annotated[int, Query(ge=0, le=5)] = 2,
        include_historical: Annotated[bool, Query()] = False,
    ) -> SubgraphResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        if (artifact_id is None) == (actor_id is None):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Provide exactly one of artifact_id or actor_id.",
            ) from None
        if artifact_id is not None:
            anchor_lit: Literal["artifact", "actor"] = "artifact"
            anchor_uuid: uuid.UUID = artifact_id
        else:
            anchor_lit = "actor"
            assert actor_id is not None
            anchor_uuid = actor_id
        nodes, edges, trunc, treason = cq.build_subgraph(
            db,
            tenant_id=claims.tenant_id,
            anchor_type=anchor_lit,
            anchor_id=anchor_uuid,
            depth=min(depth, 5),
            max_nodes=400,
            current_only=not include_historical,
        )
        return SubgraphResponse(
            anchor=SubgraphAnchor(type=anchor_lit, id=anchor_uuid),
            depth=depth,
            nodes=[SubgraphNode.model_validate(n) for n in nodes],
            edges=[
                SubgraphEdge(
                    id=uuid.UUID(e["id"]),
                    source_id=uuid.UUID(e["source_id"]),
                    target_id=uuid.UUID(e["target_id"]),
                    relation_kind=e["relation_kind"],
                    directed=bool(e["directed"]),
                    valid_from=e["valid_from"],
                    valid_to=e["valid_to"],
                )
                for e in edges
            ],
            truncated=trunc,
            truncation_reason=treason,
        )

    @r.post("/canonical/drain")
    def trigger_canonical_drain(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        connection_id: Annotated[uuid.UUID, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> dict[str, Any]:
        """Safety-net / manual Step 3 drain for a connection."""
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=claims.tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None
        if connector == CONNECTOR_GITHUB:
            m = drain_github_canonical(
                db,
                tenant_id=claims.tenant_id,
                connection_id=connection_id,
            )
        elif connector == CONNECTOR_LINEAR:
            m = drain_linear_canonical(
                db,
                tenant_id=claims.tenant_id,
                connection_id=connection_id,
            )
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported connector for canonical drain: {connector}",
            ) from None
        return {
            "raw_rows_processed": m.raw_rows_processed,
            "batches_committed": m.batches_committed,
        }

    @r.post("/canonical/reset-and-resync")
    def reset_and_resync_canonical(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        settings: Annotated[Any, Depends(settings_dep)],
        connection_id: Annotated[uuid.UUID, Query()],
        confirm: Annotated[str, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> dict[str, Any]:
        if connector != CONNECTOR_GITHUB:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Only '{CONNECTOR_GITHUB}' is supported.",
            ) from None
        if confirm.strip().upper() != "RESET":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Missing confirmation. Pass confirm=RESET.",
            ) from None
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=claims.tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None

        reset_github_pipeline_state(
            db,
            tenant_id=claims.tenant_id,
            connection_id=connection_id,
        )
        run = run_github_poll_ingestion_for_tenant(db, settings, claims.tenant_id)
        if run.status == RUN_STATUS_SUCCEEDED:
            p = drain_github_projections(
                db,
                tenant_id=claims.tenant_id,
                connection_id=run.connection_id,
            )
            c = drain_github_canonical(
                db,
                tenant_id=claims.tenant_id,
                connection_id=run.connection_id,
            )
        else:
            p = None
            c = None
        return {
            "reset": True,
            "connection_id": str(connection_id),
            "ingestion_run_id": str(run.id),
            "ingestion_status": run.status,
            "projection_rows_processed": p.raw_rows_processed if p else 0,
            "canonical_rows_processed": c.raw_rows_processed if c else 0,
            "warning": (
                None
                if run.status == RUN_STATUS_SUCCEEDED
                else "Ingestion failed; projections/canonical not drained."
            ),
        }

    @r.post("/canonical/rebuild-from-step1")
    def rebuild_from_step1_github(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
        connection_id: Annotated[uuid.UUID, Query()],
        confirm: Annotated[str, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> dict[str, Any]:
        """Wipe Step 2+3 and replay all existing raw rows (no GitHub poll)."""
        if connector != CONNECTOR_GITHUB:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Only '{CONNECTOR_GITHUB}' is supported.",
            ) from None
        if confirm.strip().upper() != "REBUILD":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Missing confirmation. Pass confirm=REBUILD.",
            ) from None
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=claims.tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None
        p, c = rebuild_derived_from_step1_github(
            db,
            tenant_id=claims.tenant_id,
            connection_id=connection_id,
        )
        return {
            "rebuilt_from_step1": True,
            "connection_id": str(connection_id),
            "projection_rows_processed": p.raw_rows_processed,
            "canonical_rows_processed": c.raw_rows_processed,
        }

    return r
