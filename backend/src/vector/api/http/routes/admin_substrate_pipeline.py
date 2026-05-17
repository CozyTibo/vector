"""Admin HTTP — substrate pipeline runs (runtime-backed)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db
from vector.domains.cortex.retrieval.retrieval_truth_validation import (
    run_retrieval_truth_validation_suite_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_receipts import (
    build_pipeline_execution_receipt_v1,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)
from vector.infrastructure.db.repositories import tenancy as tenancy_repo


def register_substrate_pipeline_routes(router: APIRouter) -> None:
    r = APIRouter(prefix="/tenants/{tenant_id}/cortex/substrate-pipeline", tags=["cortex-substrate-pipeline"])

    @r.get("/runs")
    def list_pipeline_runs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 25,
    ) -> dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
        rows = list(
            db.scalars(
                select(CortexSubstratePipelineRun)
                .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
                .order_by(CortexSubstratePipelineRun.created_at.desc())
                .limit(limit)
            ).all()
        )
        return {
            "surface_kind": "runtime_backed",
            "runs": [
                {
                    "pipeline_run_id": str(row.id),
                    "status": row.status,
                    "trigger_kind": row.trigger_kind,
                    "current_phase_id": row.current_phase_id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                }
                for row in rows
            ],
        }

    @r.get("/runs/{pipeline_run_id}")
    def get_pipeline_run(
        tenant_id: uuid.UUID,
        pipeline_run_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
        run = db.get(CortexSubstratePipelineRun, pipeline_run_id)
        if run is None or run.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pipeline_run_not_found")
        phases = list(
            db.scalars(
                select(CortexSubstratePhaseRun)
                .where(CortexSubstratePhaseRun.pipeline_run_id == pipeline_run_id)
                .order_by(CortexSubstratePhaseRun.phase_ordinal.asc())
            ).all()
        )
        receipt = build_pipeline_execution_receipt_v1(db, pipeline_run_id=pipeline_run_id)
        return {
            "surface_kind": "runtime_backed",
            "run": {
                "pipeline_run_id": str(run.id),
                "status": run.status,
                "trigger_kind": run.trigger_kind,
                "bundle_id": run.bundle_id,
                "error_detail": run.error_detail,
                "summary_json": dict(run.summary_json or {}),
            },
            "phases": [
                {
                    "phase_id": p.phase_id,
                    "status": p.status,
                    "attempt": p.attempt,
                    "output_json": dict(p.output_json or {}),
                    "error_detail": p.error_detail,
                    "started_at": p.started_at.isoformat() if p.started_at else None,
                    "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                }
                for p in phases
            ],
            "execution_receipt": receipt,
        }

    @r.get("/runs/{pipeline_run_id}/stuck-phases")
    def get_stuck_phases(
        tenant_id: uuid.UUID,
        pipeline_run_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        run = db.get(CortexSubstratePipelineRun, pipeline_run_id)
        if run is None or run.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pipeline_run_not_found")
        phases = list(
            db.scalars(
                select(CortexSubstratePhaseRun).where(
                    CortexSubstratePhaseRun.pipeline_run_id == pipeline_run_id,
                    CortexSubstratePhaseRun.status.in_(("queued", "running", "failed")),
                )
            ).all()
        )
        return {
            "surface_kind": "runtime_backed",
            "stuck_phases": [
                {"phase_id": p.phase_id, "status": p.status, "error_detail": p.error_detail}
                for p in phases
            ],
        }

    @r.get("/retrieval-truth-validation")
    def get_retrieval_truth_validation(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
        return run_retrieval_truth_validation_suite_v1(db, tenant_id=tenant_id)

    @r.get("/reconstruction-catalog")
    def get_reconstruction_catalog() -> dict[str, Any]:
        from vector.domains.cortex.retrieval.runtime.reconstruction import build_reconstruction_catalog_v1

        return build_reconstruction_catalog_v1()

    router.include_router(r)
