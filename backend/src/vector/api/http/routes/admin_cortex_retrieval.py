"""Admin HTTP — Phase 07 retrieval + lineage + durable replay."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db
from vector.domains.cortex.continuity.runtime.continuity_topology_graph import (
    build_continuity_topology_v1,
)
from vector.domains.cortex.retrieval.retrieval_artifact_lineage import (
    build_retrieval_lineage_explorer_catalog_v1,
    build_retrieval_lineage_explorer_chain_v1,
    get_retrieval_lineage_gap_total_v1,
    get_retrieval_lineage_truncated_total_v1,
)
from vector.domains.cortex.retrieval.anti_goals import (
    RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
    RetrievalAntiGoalViolationError,
)
from vector.domains.cortex.retrieval.phase_boundaries import (
    build_retrieval_phase_boundary_catalog_v1,
    RetrievalPhaseBoundaryError,
)
from vector.domains.cortex.retrieval.retrieval_ingress import (
    RetrievalIngressError,
    build_retrieval_ingress_law_catalog_v1,
    build_retrieval_provenance_inspector_fields_v1,
    validate_retrieval_ingress_artifact_kind_v1,
)
from vector.domains.cortex.retrieval.query_contract import (
    RetrievalQueryContractError,
    build_retrieval_query_contract_catalog_v1,
)
from vector.domains.cortex.retrieval.query_execution import (
    RETRIEVAL_QUERY_EXECUTION_PHASES_V1,
    RetrievalQueryExecutionError,
    execute_retrieval_query_envelope_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_matrix import (
    build_retrieval_legality_matrix_catalog_v1,
    build_retrieval_queries_by_legality_histogram_v1,
)
from vector.domains.cortex.retrieval.retrieval_runtime_legality_matrix import (
    build_retrieval_runtime_legality_matrix_catalog_v1,
)
from vector.domains.cortex.retrieval.retrieval_addressing import (
    build_retrieval_addressing_catalog_v1,
)
from vector.domains.cortex.retrieval.retrieval_provenance_evidence import (
    build_retrieval_provenance_inspector_catalog_v1,
)
from vector.domains.cortex.retrieval.retrieval_bounded_caps import (
    build_retrieval_omission_explorer_catalog_v1,
)
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    build_retrieval_coverage_catalog_v1,
    build_retrieval_overview_catalog_v1,
)
from vector.domains.cortex.retrieval.retrieval_observability import (
    build_retrieval_health_strip_v1,
    build_retrieval_observability_catalog_v1,
    build_retrieval_runtime_health_v1,
    get_retrieval_legality_failures_total_v1,
    get_retrieval_queries_total_v1,
    snapshot_retrieval_metrics_v1,
)
from vector.domains.cortex.retrieval.retrieval_degradation_taxonomy import (
    build_retrieval_degradation_topology_catalog_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    RetrievalIndexMaterializationError,
    bootstrap_retrieval_index_from_upstream_v1,
    build_retrieval_index_catalog_v1,
    compute_index_lag_epochs_v1,
    run_retrieval_index_rebuild_v1,
)
from vector.domains.cortex.retrieval.retrieval_ranking_selection import (
    build_retrieval_ranking_selection_catalog_v1,
)
from vector.domains.cortex.retrieval.retrieval_temporal import (
    build_retrieval_temporal_explorer_catalog_v1,
)
from vector.domains.cortex.retrieval.retrieval_tcre_binding import (
    RetrievalTcreBindingError,
    build_retrieval_tcre_binding_catalog_v1,
    build_tcre_handoff_lookup_map_v1,
    get_retrieval_tcre_bind_failures_total_v1,
    load_tcre_reconstruction_job_v1,
)
from vector.domains.cortex.retrieval.retrieval_octs_binding import (
    RetrievalOctsBindingError,
    build_retrieval_traversal_binding_catalog_v1,
    get_retrieval_walk_bind_failures_total_v1,
    query_walk_scope_v1,
)
from vector.domains.cortex.retrieval.retrieval_graph_binding import (
    RetrievalGraphBindingError,
    build_retrieval_graph_binding_catalog_v1,
    get_retrieval_graph_bind_failures_total_v1,
    get_retrieval_graph_orphan_detected_total_v1,
    query_graph_scope_v1,
)
from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
    RetrievalReplayEquivalenceError,
)
from vector.domains.cortex.retrieval.retrieval_replay_equivalence_proofs import (
    build_retrieval_replay_inspector_catalog_v1,
)
from vector.domains.cortex.retrieval.retrieval_control_plane import (
    build_retrieval_control_plane_v1,
    build_retrieval_control_plane_surface_checklist_v1,
    list_retrieval_query_audit_trail_v1,
)
from vector.domains.cortex.retrieval.retrieval_certification_pack import (
    build_retrieval_certification_pack_snapshot_v1,
)
from vector.domains.cortex.retrieval.retrieval_program_closure import (
    build_retrieval_program_closure_snapshot_v1,
)
from vector.domains.cortex.retrieval.retrieval_readiness_economics import (
    build_retrieval_readiness_economics_receipt_v1,
)
from vector.contracts.admin import (
    AdminCortexRetrievalCertificationPackSnapshotResponse,
    AdminCortexRetrievalProgramClosureResponse,
)
from vector.domains.cortex.retrieval.retrieval_tenant_verification_slice import (
    build_org_graph_retrieval_verification_slice_v1,
    compute_retrieval_verification_slice_hash_v1,
)
from vector.domains.cortex.retrieval.retrieval_operator_workflows import (
    RetrievalOperatorWorkflowsError,
    assert_retrieval_index_rebuild_confirmation_v1,
    build_retrieval_operator_workflows_catalog_v1,
    list_remediation_links_for_omissions_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_projection import (
    RetrievalLegalityError,
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

    @r.get("/legality", response_model=None)
    def get_retrieval_legality(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        matrix = build_retrieval_legality_matrix_catalog_v1(tenant_id=tenant_id)
        return {
            **matrix,
            "phase_boundaries": build_retrieval_phase_boundary_catalog_v1(),
            "ingress_law": build_retrieval_ingress_law_catalog_v1(),
            "provenance_inspector_fields": build_retrieval_provenance_inspector_fields_v1(),
            "query_contract": build_retrieval_query_contract_catalog_v1(),
            "query_execution_phases": list(RETRIEVAL_QUERY_EXECUTION_PHASES_V1),
            "retrieval_queries_by_legality": build_retrieval_queries_by_legality_histogram_v1(
                db, tenant_id=tenant_id
            ),
        }

    @r.get("/runtime-legality-matrix", response_model=None)
    def get_retrieval_runtime_legality_matrix(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        doc = build_retrieval_runtime_legality_matrix_catalog_v1(db, tenant_id=tenant_id)
        doc["retrieval_queries_by_legality"] = build_retrieval_queries_by_legality_histogram_v1(
            db, tenant_id=tenant_id
        )
        return doc

    @r.get("/index", response_model=None)
    def get_retrieval_index(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_retrieval_index_catalog_v1(tenant_id=tenant_id)
        catalog["index_lag_epochs"] = compute_index_lag_epochs_v1(db, tenant_id=tenant_id)
        return catalog

    @r.post("/index/rebuild", response_model=None)
    def post_retrieval_index_rebuild(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any], Body(default_factory=dict)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        try:
            assert_retrieval_index_rebuild_confirmation_v1(body.get("confirmation_phrase"))
            result = run_retrieval_index_rebuild_v1(
                db,
                tenant_id=tenant_id,
                index_epoch=str(body.get("index_epoch")).strip() if body.get("index_epoch") else None,
            )
            db.commit()
            return result
        except RetrievalOperatorWorkflowsError as exc:
            return JSONResponse(status_code=403, content={"error": exc.code, "detail": exc.detail})
        except RetrievalIndexMaterializationError as exc:
            db.rollback()
            return JSONResponse(status_code=400, content={"error": exc.code, "detail": exc.detail})

    @r.post("/index/bootstrap", response_model=None)
    def post_retrieval_index_bootstrap(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any], Body(default_factory=dict)],
    ) -> JSONResponse | dict[str, Any]:
        """Materialize index from completed TCRE jobs / walks / org links, then publish epoch."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        try:
            result = bootstrap_retrieval_index_from_upstream_v1(
                db,
                tenant_id=tenant_id,
                index_epoch=str(body.get("index_epoch")).strip() if body.get("index_epoch") else None,
                max_tcre_jobs=int(body.get("max_tcre_jobs") or 100),
                max_graph_links=int(body.get("max_graph_links") or 500),
            )
            db.commit()
            return result
        except RetrievalIndexMaterializationError as exc:
            db.rollback()
            return JSONResponse(status_code=400, content={"error": exc.code, "detail": exc.detail})

    @r.get("/omission-explorer", response_model=None)
    def get_retrieval_omission_explorer(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_retrieval_omission_explorer_catalog_v1()
        catalog["tenant_id"] = str(tenant_id)
        return catalog

    @r.get("/degradation-topology", response_model=None)
    def get_retrieval_degradation_topology(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return build_retrieval_degradation_topology_catalog_v1(tenant_id=str(tenant_id))

    @r.get("/ranking-selection", response_model=None)
    def get_retrieval_ranking_selection(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_retrieval_ranking_selection_catalog_v1()
        catalog["tenant_id"] = str(tenant_id)
        return catalog

    @r.get("/graph-binding", response_model=None)
    def get_retrieval_graph_binding(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        scope_kind: Annotated[str | None, Query()] = None,
        org_entity_id: Annotated[str | None, Query()] = None,
        org_link_id: Annotated[str | None, Query()] = None,
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_retrieval_graph_binding_catalog_v1()
        catalog["tenant_id"] = str(tenant_id)
        catalog["retrieval_graph_orphan_detected_total"] = get_retrieval_graph_orphan_detected_total_v1()
        catalog["retrieval_graph_bind_failures_total"] = get_retrieval_graph_bind_failures_total_v1()
        if scope_kind:
            try:
                catalog["graph_scope_result"] = query_graph_scope_v1(
                    db,
                    tenant_id=tenant_id,
                    scope_kind=scope_kind,
                    org_entity_id=org_entity_id,
                    org_link_id=org_link_id,
                )
            except RetrievalGraphBindingError as exc:
                return JSONResponse(
                    status_code=400, content={"error": exc.code, "detail": exc.detail}
                )
        return catalog

    @r.get("/traversal-binding", response_model=None)
    def get_retrieval_traversal_binding(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        scope_kind: Annotated[str | None, Query()] = None,
        walk_id: Annotated[str | None, Query()] = None,
        walk_result_hash: Annotated[str | None, Query()] = None,
        traversal_epoch: Annotated[str | None, Query()] = None,
        graph_eligible: Annotated[bool, Query()] = False,
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_retrieval_traversal_binding_catalog_v1()
        catalog["tenant_id"] = str(tenant_id)
        catalog["retrieval_walk_bind_failures_total"] = get_retrieval_walk_bind_failures_total_v1()
        if scope_kind:
            try:
                catalog["walk_scope_result"] = query_walk_scope_v1(
                    db,
                    tenant_id=tenant_id,
                    scope_kind=scope_kind,
                    walk_id=walk_id,
                    walk_result_hash=walk_result_hash,
                    traversal_epoch=traversal_epoch,
                    graph_eligible=graph_eligible,
                )
            except RetrievalOctsBindingError as exc:
                return JSONResponse(
                    status_code=400, content={"error": exc.code, "detail": exc.detail}
                )
        return catalog

    @r.get("/tcre-binding", response_model=None)
    def get_retrieval_tcre_binding(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        job_id: Annotated[str | None, Query()] = None,
        replay_identity: Annotated[str | None, Query()] = None,
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_retrieval_tcre_binding_catalog_v1()
        catalog["tenant_id"] = str(tenant_id)
        catalog["retrieval_tcre_bind_failures_total"] = get_retrieval_tcre_bind_failures_total_v1()
        if job_id:
            try:
                job = load_tcre_reconstruction_job_v1(
                    db, tenant_id=tenant_id, job_id=job_id
                )
            except (ValueError, TypeError) as exc:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_job_id", "detail": str(exc)},
                )
            if job is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": "tcre_job_not_found"},
                )
            replay = (replay_identity or str(job.summary_json.get("replay_identity") or "")).strip()
            if not replay:
                return JSONResponse(
                    status_code=400,
                    content={"error": "replay_identity_required"},
                )
            try:
                catalog["lookup_map"] = build_tcre_handoff_lookup_map_v1(
                    job=job,
                    artifacts=list(job.artifacts),
                    replay_identity=replay,
                )
            except RetrievalTcreBindingError as exc:
                return JSONResponse(
                    status_code=400, content={"error": exc.code, "detail": exc.detail}
                )
        return catalog

    @r.get("/temporal-explorer", response_model=None)
    def get_retrieval_temporal_explorer(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_retrieval_temporal_explorer_catalog_v1()
        catalog["tenant_id"] = str(tenant_id)
        return catalog

    @r.get("/provenance-inspector", response_model=None)
    def get_retrieval_provenance_inspector(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_retrieval_provenance_inspector_catalog_v1()
        catalog["tenant_id"] = str(tenant_id)
        catalog["ingress_inspector_fields"] = build_retrieval_provenance_inspector_fields_v1()
        return catalog

    @r.get("/addressing", response_model=None)
    def get_retrieval_addressing(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_retrieval_addressing_catalog_v1()
        catalog["tenant_id"] = str(tenant_id)
        return catalog

    @r.get("/replay-inspector", response_model=None)
    def get_retrieval_replay_inspector(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return build_retrieval_replay_inspector_catalog_v1(tenant_id=str(tenant_id))

    @r.get("/query-contract")
    def get_retrieval_query_contract(tenant_id: uuid.UUID) -> dict[str, Any]:
        _ = tenant_id
        return build_retrieval_query_contract_catalog_v1()

    @r.get("/ingress")
    def get_retrieval_ingress_law(tenant_id: uuid.UUID) -> dict[str, Any]:
        _ = tenant_id
        return {
            "ingress_law": build_retrieval_ingress_law_catalog_v1(),
            "provenance_inspector_fields": build_retrieval_provenance_inspector_fields_v1(),
        }

    @r.get("/workflows", response_model=None)
    def get_retrieval_operator_workflows(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        _ = db
        return build_retrieval_operator_workflows_catalog_v1(tenant_id=str(tenant_id))

    @r.get("/control-plane", response_model=None)
    def get_retrieval_control_plane(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return build_retrieval_control_plane_v1(db, tenant_id=tenant_id)

    @r.get("/audit", response_model=None)
    def get_retrieval_query_audit_trail(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query()] = 50,
        result_legality_class: Annotated[str | None, Query()] = None,
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return {
            "tenant_id": str(tenant_id),
            "audit_rows": list_retrieval_query_audit_trail_v1(
                db,
                tenant_id=tenant_id,
                limit=limit,
                result_legality_class=result_legality_class,
            ),
            "surface_checklist": build_retrieval_control_plane_surface_checklist_v1(),
        }

    @r.get("/readiness-economics", response_model=None)
    def get_retrieval_readiness_economics(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        profile: Annotated[str, Query()] = "clean",
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        _ = db
        prof: Literal["clean", "hostile"] = (
            "hostile" if profile.strip().lower() == "hostile" else "clean"
        )
        return build_retrieval_readiness_economics_receipt_v1(tenant_id=tenant_id, profile=prof)

    @r.get(
        "/program-closure",
        response_model=AdminCortexRetrievalProgramClosureResponse,
    )
    def get_retrieval_program_closure_snapshot(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexRetrievalProgramClosureResponse:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "tenant_not_found"},
            )
        raw = build_retrieval_program_closure_snapshot_v1(db, tenant_id=tenant_id)
        return AdminCortexRetrievalProgramClosureResponse.model_validate(raw)

    @r.get(
        "/certification-pack",
        response_model=AdminCortexRetrievalCertificationPackSnapshotResponse,
    )
    def get_retrieval_certification_pack_snapshot(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexRetrievalCertificationPackSnapshotResponse:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "tenant_not_found"},
            )
        _ = db
        raw = build_retrieval_certification_pack_snapshot_v1(tenant_id=tenant_id)
        return AdminCortexRetrievalCertificationPackSnapshotResponse.model_validate(raw)

    @r.get("/tenant-verification-slice", response_model=None)
    def get_retrieval_tenant_verification_slice(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        verification_run_id: Annotated[str | None, Query()] = None,
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        slice_body = build_org_graph_retrieval_verification_slice_v1(
            db,
            tenant_id=tenant_id,
            verification_run_id=verification_run_id,
        )
        return {
            "slice": slice_body,
            "retrieval_slice_hash": compute_retrieval_verification_slice_hash_v1(slice_body),
        }

    @r.get("/health", response_model=None)
    def get_retrieval_runtime_health(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return build_retrieval_runtime_health_v1(db, tenant_id=tenant_id)

    @r.get("/observability", response_model=None)
    def get_retrieval_observability_catalog(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_retrieval_observability_catalog_v1()
        catalog["tenant_id"] = str(tenant_id)
        catalog["metrics"] = snapshot_retrieval_metrics_v1()
        catalog["retrieval_queries_total"] = get_retrieval_queries_total_v1()
        catalog["retrieval_legality_failures_total"] = get_retrieval_legality_failures_total_v1()
        return catalog

    @r.get("/overview", response_model=None)
    def get_retrieval_overview(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        overview = build_retrieval_overview_catalog_v1(db, tenant_id=tenant_id)
        overview["health_strip"] = build_retrieval_health_strip_v1(db, tenant_id=tenant_id)
        return overview

    @r.get("/coverage", response_model=None)
    def get_retrieval_coverage(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return build_retrieval_coverage_catalog_v1(db, tenant_id=tenant_id)

    @r.post("/query", response_model=None)
    def post_retrieval_query(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any], Body(...)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
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

    @r.get("/lineage-explorer", response_model=None)
    def get_lineage_explorer_catalog(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_retrieval_lineage_explorer_catalog_v1()
        catalog["tenant_id"] = str(tenant_id)
        catalog["retrieval_lineage_gap_total"] = get_retrieval_lineage_gap_total_v1()
        catalog["retrieval_lineage_truncated_total"] = get_retrieval_lineage_truncated_total_v1()
        return catalog

    @r.get("/lineage/{artifact_kind}/{artifact_ref:path}", response_model=None)
    def get_lineage_explorer(
        tenant_id: uuid.UUID,
        artifact_kind: str,
        artifact_ref: str,
        db: Annotated[Session, Depends(get_db)],
        max_lineage_hops: Annotated[int, Query()] = 64,
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
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
