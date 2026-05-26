"""Admin HTTP — synthesis keep-list (R6: jobs, debugger, health)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db
from vector.contracts.admin import AdminCortexSynthesisRuntimeHealthResponse
from vector.domains.cortex.synthesis.synthesis_observability import build_synthesis_runtime_health_v1
from vector.domains.cortex.synthesis.synthesis_job_inspector_v1 import (
    build_synthesis_job_inspector_v1,
)
from vector.domains.cortex.synthesis.synthesis_operator_workflows import (
    SynthesisOperatorWorkflowsError,
    build_synthesis_job_debugger_v1,
    list_synthesis_jobs_admin_v1,
    retry_synthesis_job_v1,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import (
    SynthesisOrchestratorError,
    get_synthesis_job_detail_v1,
)
from vector.infrastructure.db.repositories import tenancy as tenancy_repo


def register_cortex_synthesis_routes(router: APIRouter) -> None:
    sr = APIRouter(prefix="/tenants/{tenant_id}/cortex/synthesis", tags=["admin-cortex-synthesis"])

    def _assert_tenant(db: Session, tenant_id: uuid.UUID) -> None:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")

    @sr.get("/health", response_model=None)
    def get_synthesis_runtime_health(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisRuntimeHealthResponse:
        _assert_tenant(db, tenant_id)
        raw = build_synthesis_runtime_health_v1(db, tenant_id=tenant_id)
        return AdminCortexSynthesisRuntimeHealthResponse.model_validate(raw)

    @sr.get("/jobs", response_model=None)
    def list_synthesis_jobs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> JSONResponse | dict[str, Any]:
        _assert_tenant(db, tenant_id)
        return list_synthesis_jobs_admin_v1(db, tenant_id=tenant_id, limit=limit)

    @sr.get("/jobs/{job_id}", response_model=None)
    def get_synthesis_job_detail(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        _assert_tenant(db, tenant_id)
        try:
            return get_synthesis_job_detail_v1(db, tenant_id=tenant_id, job_id=job_id)
        except SynthesisOrchestratorError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.get("/jobs/{job_id}/debugger", response_model=None)
    def get_synthesis_job_debugger(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        _assert_tenant(db, tenant_id)
        try:
            return build_synthesis_job_debugger_v1(db, tenant_id=tenant_id, job_id=job_id)
        except SynthesisOrchestratorError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.get("/jobs/{job_id}/inspector", response_model=None)
    def get_synthesis_job_inspector(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        _assert_tenant(db, tenant_id)
        try:
            return build_synthesis_job_inspector_v1(db, tenant_id=tenant_id, job_id=job_id)
        except SynthesisOrchestratorError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.post("/jobs/{job_id}/retry", response_model=None)
    def post_synthesis_job_retry(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        _assert_tenant(db, tenant_id)
        try:
            out = retry_synthesis_job_v1(db, tenant_id=tenant_id, job_id=job_id)
            db.commit()
            return out
        except SynthesisOrchestratorError as exc:
            db.rollback()
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )
        except SynthesisOperatorWorkflowsError as exc:
            db.rollback()
            return JSONResponse(
                status_code=400,
                content={"error": exc.code, "detail": exc.detail},
            )

    router.include_router(sr)
