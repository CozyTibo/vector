"""Phase 08 P08-06 — Celery entrypoint for synthesis job FSM."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.synthesis.synthesis_orchestrator import (
    execute_synthesis_job_envelope_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK_RUN = "vector.cortex.synthesis.run_synthesis_job"

CELERY_TASK_NAME_RUN_SYNTHESIS_JOB = _TASK_RUN


@celery_app.task(name=_TASK_RUN)
def run_synthesis_job_task(tenant_id: str, job_id: str) -> dict[str, Any]:
    tid = uuid.UUID(tenant_id)
    jid = uuid.UUID(job_id)
    _LOGGER.info("synthesis_job_start tenant_id=%s job_id=%s", tenant_id, job_id)
    with session_scope() as session:
        job = session.get(CortexSynthesisJob, jid)
        if job is None or job.tenant_id != tid:
            msg = "synthesis_job_not_found_or_tenant_mismatch"
            raise ValueError(msg)
        if job.status != "queued":
            return {
                "tenant_id": tenant_id,
                "job_id": job_id,
                "status": job.status,
                "skipped": True,
            }
        summary = execute_synthesis_job_envelope_v1(
            session,
            tenant_id=tid,
            body=dict(job.envelope_json or {}),
            job_id=jid,
        )
        session.commit()
    _LOGGER.info("synthesis_job_done tenant_id=%s job_id=%s", tenant_id, job_id)
    return {"tenant_id": tenant_id, "job_id": job_id, "summary": summary}
