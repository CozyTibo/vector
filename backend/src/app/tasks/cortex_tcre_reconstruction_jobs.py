"""Phase 06 RUNTIME-01 — Celery entrypoint for TCRE reconstruction jobs."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    execute_tcre_reconstruction_job_v1,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK_RUN = "vector.cortex.reasoning.run_tcre_reconstruction_job"

CELERY_TASK_NAME_RUN_TCRE_RECONSTRUCTION_JOB = _TASK_RUN


@celery_app.task(name=_TASK_RUN)
def run_tcre_reconstruction_job_task(tenant_id: str, job_id: str) -> dict[str, Any]:
    tid = uuid.UUID(tenant_id)
    jid = uuid.UUID(job_id)
    _LOGGER.info("tcre_reconstruction_start tenant_id=%s job_id=%s", tenant_id, job_id)
    chained: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    with session_scope() as session:
        job = session.get(CortexTcreReconstructionJob, jid)
        if job is None or job.tenant_id != tid:
            msg = "tcre_reconstruction_job_not_found_or_tenant_mismatch"
            raise ValueError(msg)
        if job.status != "queued":
            return {
                "tenant_id": tenant_id,
                "job_id": job_id,
                "status": job.status,
                "skipped": True,
            }
        summary = execute_tcre_reconstruction_job_v1(session, job)
        if job.status == "completed":
            from vector.domains.cortex.retrieval.retrieval_index_materialization import (
                materialize_retrieval_index_incremental_after_tcre_v1,
            )
            from vector.domains.cortex.substrate_pipeline.orchestrator import (
                on_tcre_job_completed_for_pipeline_v1,
            )

            scope = dict(job.scope_json or {})
            prid_raw = scope.get("substrate_pipeline_run_id")
            prid = uuid.UUID(str(prid_raw)) if prid_raw else None
            materialize_retrieval_index_incremental_after_tcre_v1(
                session,
                tenant_id=tid,
                job=job,
                pipeline_run_id=prid,
            )
            chained = on_tcre_job_completed_for_pipeline_v1(
                session,
                tenant_id=tid,
                job_scope=scope,
                tcre_job_id=jid,
                tcre_job_status=str(job.status),
            )
        session.commit()
    _LOGGER.info("tcre_reconstruction_done tenant_id=%s job_id=%s", tenant_id, job_id)
    return {"tenant_id": tenant_id, "job_id": job_id, "summary": summary, "pipeline_chain": chained}
