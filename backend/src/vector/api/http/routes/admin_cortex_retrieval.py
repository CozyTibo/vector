"""Admin HTTP — Phase 07 retrieval + lineage + durable replay."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db
from vector.domains.cortex.continuity.runtime.continuity_topology_graph import (
    build_continuity_topology_v1,
)
from vector.domains.cortex.lineage.lineage_chain_builder import build_artifact_lineage_chain_v1
from vector.domains.cortex.lineage.lineage_explainability_projection import (
    build_lineage_explainability_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_projection import (
    RetrievalLegalityError,
    retrieval_policy_digest_v1,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)
from vector.domains.cortex.traversal.runtime.traversal_lineage_repository import (
    list_walk_replay_lineage_v1,
)
from vector.domains.cortex.traversal.runtime.traversal_equivalence_verifier import (
    verify_traversal_replay_equivalence_v1,
)
from vector.infrastructure.db.repositories import tenancy as tenancy_repo


def register_cortex_retrieval_routes(router: APIRouter) -> None:
    r = APIRouter(prefix="/tenants/{tenant_id}/cortex/retrieval", tags=["admin-cortex-retrieval"])

    @r.get("/legality")
    def get_retrieval_legality(tenant_id: uuid.UUID) -> dict[str, Any]:
        return {
            "retrieval_policy_digest": retrieval_policy_digest_v1(),
            "legality_classes": sorted(
                [
                    "retrieval_replay_safe",
                    "retrieval_degraded",
                    "retrieval_partial",
                    "retrieval_unverifiable",
                ]
            ),
        }

    @r.get("/coverage", response_model=None)
    def get_retrieval_coverage(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        from sqlalchemy import func, select
        from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry

        total = int(
            db.scalar(
                select(func.count())
                .select_from(CortexRetrievalIndexEntry)
                .where(CortexRetrievalIndexEntry.tenant_id == tenant_id)
            )
            or 0
        )
        safe = int(
            db.scalar(
                select(func.count())
                .select_from(CortexRetrievalIndexEntry)
                .where(
                    CortexRetrievalIndexEntry.tenant_id == tenant_id,
                    CortexRetrievalIndexEntry.retrieval_legality_class == "retrieval_replay_safe",
                )
            )
            or 0
        )
        return {
            "tenant_id": str(tenant_id),
            "indexed_count": total,
            "replay_safe_count": safe,
            "coverage_percent": round(100.0 * safe / total, 2) if total else 0.0,
        }

    @r.post("/query", response_model=None)
    def post_retrieval_query(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any], Body(...)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        lookup_id = str(body.get("retrieval_lookup_id") or "").strip()
        if not lookup_id:
            return JSONResponse(status_code=400, content={"error": "retrieval_lookup_id_required"})
        try:
            return execute_retrieval_query_v1(
                db,
                tenant_id=tenant_id,
                retrieval_lookup_id=lookup_id,
                expected_replay_identity=body.get("expected_replay_identity"),
            )
        except RetrievalLegalityError as exc:
            return JSONResponse(status_code=403, content={"error": exc.code, "detail": exc.detail})

    @r.get("/lineage/{artifact_kind}/{artifact_ref:path}", response_model=None)
    def get_lineage_explorer(
        tenant_id: uuid.UUID,
        artifact_kind: str,
        artifact_ref: str,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        chain = build_artifact_lineage_chain_v1(
            db,
            tenant_id=tenant_id,
            terminal_artifact_kind=artifact_kind,
            terminal_artifact_ref=artifact_ref,
        )
        return {
            "chain": chain,
            "explainability": build_lineage_explainability_v1(chain),
        }

    @r.get("/walks/{walk_id}/replay-lineage")
    def get_walk_replay_lineage(
        tenant_id: uuid.UUID,
        walk_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        return {
            "lineage": list_walk_replay_lineage_v1(db, tenant_id=tenant_id, walk_id=walk_id),
        }

    @r.get("/walks/replay-equivalence")
    def get_traversal_replay_equivalence(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        replay_identity: Annotated[str, Query()],
    ) -> dict[str, Any]:
        return verify_traversal_replay_equivalence_v1(
            db, tenant_id=tenant_id, replay_identity=replay_identity
        )

    @r.get("/continuity-topology")
    def get_continuity_topology(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        return build_continuity_topology_v1(db, tenant_id=tenant_id)

    router.include_router(r)
