"""Admin HTTP — retrieval keep-list (R6: lineage, query, health, walks)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db
from vector.domains.cortex.continuity.runtime.continuity_topology_graph import (
    build_continuity_topology_v1,
)
from vector.domains.cortex.retrieval.anti_goals import (
    RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
    RetrievalAntiGoalViolationError,
)
from vector.domains.cortex.retrieval.phase_boundaries import RetrievalPhaseBoundaryError
from vector.domains.cortex.retrieval.query_contract import RetrievalQueryContractError
from vector.domains.cortex.retrieval.query_execution import (
    RetrievalQueryExecutionError,
    execute_retrieval_query_envelope_v1,
)
from vector.domains.cortex.retrieval.retrieval_artifact_lineage import (
    build_retrieval_lineage_explorer_chain_v1,
)
from vector.domains.cortex.retrieval.retrieval_ingress import (
    RetrievalIngressError,
    validate_retrieval_ingress_artifact_kind_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_projection import RetrievalLegalityError
from vector.domains.cortex.retrieval.retrieval_index_row_inspector_v1 import (
    build_retrieval_index_row_inspector_v1,
)
from vector.domains.cortex.retrieval.retrieval_observability import build_retrieval_runtime_health_v1
from vector.domains.cortex.retrieval.retrieval_operator_workflows import (
    list_remediation_links_for_omissions_v1,
)
from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
    RetrievalReplayEquivalenceError,
)
from vector.domains.cortex.traversal.runtime.traversal_equivalence_verifier import (
    verify_traversal_replay_equivalence_v1,
)
from vector.domains.cortex.traversal.runtime.traversal_lineage_repository import (
    list_walk_replay_lineage_v1,
)
from vector.infrastructure.db.repositories import tenancy as tenancy_repo


def register_cortex_retrieval_routes(router: APIRouter) -> None:
    r = APIRouter(prefix="/tenants/{tenant_id}/cortex/retrieval", tags=["admin-cortex-retrieval"])

    def _assert_tenant(db: Session, tenant_id: uuid.UUID) -> None:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")

    @r.get("/health", response_model=None)
    def get_retrieval_runtime_health(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        _assert_tenant(db, tenant_id)
        return build_retrieval_runtime_health_v1(db, tenant_id=tenant_id)

    @r.post("/query", response_model=None)
    def post_retrieval_query(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any], Body(...)],
    ) -> JSONResponse | dict[str, Any]:
        _assert_tenant(db, tenant_id)
        try:
            out = execute_retrieval_query_envelope_v1(
                db,
                tenant_id=tenant_id,
                body=body,
                expected_replay_identity=body.get("expected_replay_identity"),
            )
            remediation = list_remediation_links_for_omissions_v1(
                out.get("omissions") or out.get("retrieval_omission_rows") or []
            )
            if remediation:
                out["remediation_links"] = remediation
            return out
        except RetrievalQueryExecutionError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )
        except (
            RetrievalAntiGoalViolationError,
            RetrievalPhaseBoundaryError,
            RetrievalIngressError,
            RetrievalQueryContractError,
        ) as exc:
            return JSONResponse(
                status_code=403,
                content={
                    "error": exc.code,
                    "retrieval_legality_class": RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
                    "detail": getattr(exc, "detail", {}),
                },
            )
        except RetrievalReplayEquivalenceError as exc:
            return JSONResponse(
                status_code=403,
                content={"error": exc.code, "detail": exc.detail},
            )
        except RetrievalLegalityError as exc:
            return JSONResponse(status_code=403, content={"error": exc.code, "detail": exc.detail})

    @r.get("/lineage/{artifact_kind}/{artifact_ref:path}", response_model=None)
    def get_lineage_explorer(
        tenant_id: uuid.UUID,
        artifact_kind: str,
        artifact_ref: str,
        db: Annotated[Session, Depends(get_db)],
        max_lineage_hops: Annotated[int, Query()] = 64,
    ) -> JSONResponse | dict[str, Any]:
        _assert_tenant(db, tenant_id)
        try:
            validate_retrieval_ingress_artifact_kind_v1(artifact_kind)
        except RetrievalIngressError as exc:
            return JSONResponse(status_code=403, content={"error": exc.code, "detail": exc.detail})
        return build_retrieval_lineage_explorer_chain_v1(
            db,
            tenant_id=tenant_id,
            artifact_kind=artifact_kind,
            artifact_ref=artifact_ref,
            max_hops=max_lineage_hops,
        )

    @r.get("/walks/{walk_id}/replay-lineage")
    def get_walk_replay_lineage(
        tenant_id: uuid.UUID,
        walk_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        return {
            "lineage": list_walk_replay_lineage_v1(db, tenant_id=tenant_id, walk_id=walk_id),
        }

    @r.get("/walks/replay-equivalence")
    def get_traversal_replay_equivalence(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        replay_identity: Annotated[str, Query()],
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        return verify_traversal_replay_equivalence_v1(
            db, tenant_id=tenant_id, replay_identity=replay_identity
        )

    @r.get("/index-row-inspector", response_model=None)
    def get_retrieval_index_row_inspector(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: int = Query(200, ge=1, le=2000),
    ) -> JSONResponse | dict[str, Any]:
        _assert_tenant(db, tenant_id)
        return build_retrieval_index_row_inspector_v1(db, tenant_id=tenant_id, limit=limit)

    @r.get("/continuity-topology")
    def get_continuity_topology(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        return build_continuity_topology_v1(db, tenant_id=tenant_id)

    router.include_router(r)
