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

    @r.get("/runs/{pipeline_run_id}/synthesis-panel")
    def get_pipeline_synthesis_panel(
        tenant_id: uuid.UUID,
        pipeline_run_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
        run = db.get(CortexSubstratePipelineRun, pipeline_run_id)
        if run is None or run.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pipeline_run_not_found")
        from vector.domains.cortex.synthesis.synthesis_pipeline import build_pipeline_synthesis_panel_v1

        return build_pipeline_synthesis_panel_v1(
            db,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
        )

    @r.get("/operational-health")
    def get_operational_health(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
        from vector.domains.cortex.substrate_pipeline.substrate_operational_health import (
            evaluate_substrate_operational_health_v1,
        )

        return evaluate_substrate_operational_health_v1(db, tenant_id=tenant_id)

    @r.get("/runtime-maturity", deprecated=True)
    def get_runtime_maturity(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
        from vector.domains.cortex.substrate_pipeline.substrate_runtime_maturity import (
            evaluate_tenant_runtime_maturity_v1,
        )

        return evaluate_tenant_runtime_maturity_v1(db, tenant_id=tenant_id)

    @r.get("/continuation", deprecated=True)
    def get_pipeline_continuation(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
        from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
            get_continuation_for_pipeline_v1,
        )
        from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1

        running = get_running_pipeline_run_v1(db, tenant_id=tenant_id)
        if running is None:
            return {"continuation": None}
        cont = get_continuation_for_pipeline_v1(db, pipeline_run_id=running.id)
        if cont is None:
            return {"continuation": None, "pipeline_run_id": str(running.id)}
        from vector.domains.cortex.operational_runtime.substrate_continuity import (
            continuation_row_to_public_dict_v1,
        )

        return {
            "pipeline_run_id": str(running.id),
            "continuation": continuation_row_to_public_dict_v1(cont),
        }

    @r.get("/retrieval-materialization-reports")
    def list_retrieval_materialization_reports(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=50)] = 10,
    ) -> dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
        from vector.infrastructure.db.models.cortex_retrieval_materialization_report import (
            CortexRetrievalMaterializationReport,
        )

        rows = list(
            db.scalars(
                select(CortexRetrievalMaterializationReport)
                .where(CortexRetrievalMaterializationReport.tenant_id == tenant_id)
                .order_by(CortexRetrievalMaterializationReport.created_at.desc())
                .limit(limit)
            ).all()
        )
        return {
            "reports": [
                {
                    "report_id": str(row.id),
                    "pipeline_run_id": str(row.pipeline_run_id) if row.pipeline_run_id else None,
                    "retrieval_epoch": row.retrieval_epoch,
                    "accepted_rows": row.accepted_rows,
                    "skipped_rows": row.skipped_rows,
                    "tcre_candidates": row.tcre_candidates,
                    "walks_candidates": row.walks_candidates,
                    "org_link_candidates": row.org_link_candidates,
                    "skip_reasons": list(row.skip_reasons_json or []),
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ],
        }

    @router.get("/catalog/cortex/substrate-pipeline/stalled")
    def list_stalled_pipelines_catalog(
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        from vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery import (
            detect_stalled_substrate_pipelines_v1,
        )

        return {
            "stalled_pipelines": detect_stalled_substrate_pipelines_v1(db, limit=limit),
        }

    @router.get("/catalog/cortex/substrate-pipeline/runs/{pipeline_run_id}/recovery-receipts")
    def list_pipeline_recovery_receipts_catalog(
        pipeline_run_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        from vector.domains.cortex.operational_runtime.recovery_receipts import (
            list_recovery_receipts_for_pipeline_v1,
        )

        return {
            "pipeline_run_id": str(pipeline_run_id),
            "recovery_receipts": list_recovery_receipts_for_pipeline_v1(
                db,
                pipeline_run_id=pipeline_run_id,
            ),
        }

    @router.get("/catalog/cortex/substrate-pipeline/dead-letters")
    def list_substrate_pipeline_dead_letters_catalog(
        db: Annotated[Session, Depends(get_db)],
        tenant_id: Annotated[uuid.UUID | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> dict[str, Any]:
        from vector.domains.cortex.substrate_pipeline.pipeline_dead_letter import (
            list_open_dead_letters_v1,
        )

        return {
            "dead_letters": list_open_dead_letters_v1(
                db,
                tenant_id=tenant_id,
                limit=limit,
            ),
        }

    @r.get("/progression-status")
    def get_substrate_progression_status(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        pipeline_run_id: Annotated[uuid.UUID | None, Query()] = None,
        include_legacy_continuation: Annotated[bool, Query()] = False,
    ) -> dict[str, Any]:
        """Answer: did ingest propagate downstream (retrieval/synthesis materially updated)?"""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")
        from vector.domains.cortex.execution.progression_status import (
            build_substrate_progression_status_v1,
        )

        return build_substrate_progression_status_v1(
            db,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            include_legacy_continuation=include_legacy_continuation,
        )

    router.include_router(r)
