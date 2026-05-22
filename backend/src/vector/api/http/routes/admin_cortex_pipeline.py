"""Operator pipeline facade — overview, run, phase summary/explorer (admin revamp Wave 2)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, settings_dep
from vector.contracts.admin import (
    AdminCortexPipelineOverviewExecutionResponse,
    AdminCortexPipelineOverviewIngestionResponse,
    AdminCortexPipelineOverviewPhasesResponse,
    AdminCortexPipelineOverviewResponse,
    AdminCortexPipelinePhaseExplorerResponse,
    AdminCortexPipelinePhaseSummaryDetailResponse,
    AdminCortexPipelinePhaseSummaryResponse,
    AdminCortexPipelineRunRequest,
    AdminCortexPipelineRunResponse,
)
from vector.domains.cortex.ingestion.admin_overview import invalidate_cortex_ingestion_admin_caches_v1
from vector.domains.cortex.pipeline.pipeline_admin_overview import (
    build_pipeline_overview_execution_v1,
    build_pipeline_overview_ingestion_v1,
    build_pipeline_overview_phases_v1,
    build_pipeline_overview_v1,
)
from vector.domains.cortex.pipeline.pipeline_admin_run import pipeline_run_v1
from vector.domains.cortex.pipeline.pipeline_phase_views import (
    build_phase_explorer_v1,
    build_phase_summary_detail_v1,
    build_phase_summary_v1,
)
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.settings import Settings


def register_cortex_pipeline_routes(router: APIRouter) -> None:
    pr = APIRouter(prefix="/tenants/{tenant_id}/cortex/pipeline", tags=["cortex-pipeline"])

    def _assert_tenant(db: Session, tenant_id: uuid.UUID) -> None:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")

    @pr.get("/overview", response_model=AdminCortexPipelineOverviewResponse)
    def get_pipeline_overview(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexPipelineOverviewResponse:
        _assert_tenant(db, tenant_id)
        raw = build_pipeline_overview_v1(db, settings, tenant_id=tenant_id)
        return AdminCortexPipelineOverviewResponse.model_validate(raw)

    @pr.get("/overview/execution", response_model=AdminCortexPipelineOverviewExecutionResponse)
    def get_pipeline_overview_execution(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexPipelineOverviewExecutionResponse:
        _assert_tenant(db, tenant_id)
        raw = build_pipeline_overview_execution_v1(db, tenant_id=tenant_id)
        return AdminCortexPipelineOverviewExecutionResponse.model_validate(raw)

    @pr.get("/overview/phases", response_model=AdminCortexPipelineOverviewPhasesResponse)
    def get_pipeline_overview_phases(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexPipelineOverviewPhasesResponse:
        _assert_tenant(db, tenant_id)
        raw = build_pipeline_overview_phases_v1(db, tenant_id=tenant_id)
        return AdminCortexPipelineOverviewPhasesResponse.model_validate(raw)

    @pr.get("/overview/ingestion", response_model=AdminCortexPipelineOverviewIngestionResponse)
    def get_pipeline_overview_ingestion(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexPipelineOverviewIngestionResponse:
        _assert_tenant(db, tenant_id)
        raw = build_pipeline_overview_ingestion_v1(db, settings, tenant_id=tenant_id)
        return AdminCortexPipelineOverviewIngestionResponse.model_validate(raw)

    @pr.post("/run", response_model=AdminCortexPipelineRunResponse)
    def post_pipeline_run(
        tenant_id: uuid.UUID,
        body: AdminCortexPipelineRunRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexPipelineRunResponse:
        _assert_tenant(db, tenant_id)
        try:
            raw = pipeline_run_v1(
                db,
                settings,
                tenant_id=tenant_id,
                mode=body.mode,
                start_phase=body.start_phase,
                flush_mode=body.flush_mode,
                confirmation=body.confirmation,
            )
            db.commit()
            invalidate_cortex_ingestion_admin_caches_v1(tenant_id)
            return AdminCortexPipelineRunResponse.model_validate(raw)
        except ValueError as exc:
            detail = str(exc)
            if detail == "confirmation_mismatch":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Confirmation phrase does not match.",
                ) from exc
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc

    def _phase_summary_detail(
        tenant_id: uuid.UUID,
        phase: str,
        db: Session,
        settings: Settings,
    ) -> AdminCortexPipelinePhaseSummaryDetailResponse:
        _assert_tenant(db, tenant_id)
        try:
            raw = build_phase_summary_detail_v1(db, settings, tenant_id=tenant_id, phase=phase)
            return AdminCortexPipelinePhaseSummaryDetailResponse.model_validate(raw)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Register detail routes before /summary (more specific paths first).
    @pr.get(
        "/phases/{phase}/summary-detail",
        response_model=AdminCortexPipelinePhaseSummaryDetailResponse,
    )
    def get_phase_summary_detail(
        tenant_id: uuid.UUID,
        phase: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexPipelinePhaseSummaryDetailResponse:
        return _phase_summary_detail(tenant_id, phase, db, settings)

    @pr.get(
        "/phases/{phase}/summary/detail",
        response_model=AdminCortexPipelinePhaseSummaryDetailResponse,
        include_in_schema=False,
    )
    def get_phase_summary_detail_nested(
        tenant_id: uuid.UUID,
        phase: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexPipelinePhaseSummaryDetailResponse:
        return _phase_summary_detail(tenant_id, phase, db, settings)

    @pr.get("/phases/{phase}/summary", response_model=AdminCortexPipelinePhaseSummaryResponse)
    def get_phase_summary(
        tenant_id: uuid.UUID,
        phase: str,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexPipelinePhaseSummaryResponse:
        _assert_tenant(db, tenant_id)
        try:
            raw = build_phase_summary_v1(db, settings, tenant_id=tenant_id, phase=phase)
            return AdminCortexPipelinePhaseSummaryResponse.model_validate(raw)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @pr.get("/phases/{phase}/explorer", response_model=AdminCortexPipelinePhaseExplorerResponse)
    def get_phase_explorer(
        tenant_id: uuid.UUID,
        phase: str,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        connector: Annotated[str | None, Query()] = None,
        resource_type: Annotated[str | None, Query()] = None,
        search_query: Annotated[str | None, Query()] = None,
        include_health_rows: Annotated[bool, Query()] = False,
    ) -> AdminCortexPipelinePhaseExplorerResponse:
        _assert_tenant(db, tenant_id)
        try:
            raw = build_phase_explorer_v1(
                db,
                tenant_id=tenant_id,
                phase=phase,
                limit=limit,
                offset=offset,
                connector=connector,
                resource_type=resource_type,
                search_query=search_query,
                include_health_rows=include_health_rows,
            )
            return AdminCortexPipelinePhaseExplorerResponse.model_validate(raw)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    router.include_router(pr)
