"""Resume tenant execution after async TCRE instead of legacy Celery phase chaining."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.execution.lease import resume_convergence_from_waiting_v1
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    resume_pipeline_after_tcre_completion_v1,
)

_LOGGER = logging.getLogger(__name__)


def on_tcre_completed_for_convergence_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    tcre_job_id: uuid.UUID,
    tcre_job_status: str,
) -> dict[str, Any]:
    """Update continuation receipts and re-enter execution worker at phase 07."""
    legacy = resume_pipeline_after_tcre_completion_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        tcre_job_id=tcre_job_id,
        tcre_job_status=tcre_job_status,
        enqueue_phase=False,
    )
    resume_convergence_from_waiting_v1(
        session,
        tenant_id=tenant_id,
        phase_cursor=PHASE_07_RETRIEVAL,
    )
    session.flush()
    hint = enqueue_tenant_convergence_v1(tenant_id, reason="tcre_complete")
    _LOGGER.info(
        "execution_tcre_resume tenant_id=%s pipeline_run_id=%s job_id=%s",
        tenant_id,
        pipeline_run_id,
        tcre_job_id,
    )
    return {**legacy, "convergence_resume": hint, "path": "convergence_lease"}


on_tcre_completed_for_execution_v1 = on_tcre_completed_for_convergence_v1
