"""Resume tenant execution after async TCRE (single execution-lease path)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.execution.lease import resume_convergence_from_waiting_v1
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL

_LOGGER = logging.getLogger(__name__)


def on_tcre_job_terminal_for_execution_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    tcre_job_id: uuid.UUID,
    tcre_job_status: str,
) -> dict[str, Any]:
    """Re-enter execution worker at phase 07 after TCRE terminal status (no continuation enqueue)."""
    lease_resume = resume_convergence_from_waiting_v1(
        session,
        tenant_id=tenant_id,
        phase_cursor=PHASE_07_RETRIEVAL,
        pipeline_run_id=pipeline_run_id,
    )
    session.flush()
    hint = enqueue_tenant_convergence_v1(tenant_id, reason="tcre_complete")
    _LOGGER.info(
        "execution_tcre_resume tenant_id=%s pipeline_run_id=%s job_id=%s status=%s",
        tenant_id,
        pipeline_run_id,
        tcre_job_id,
        tcre_job_status,
    )
    return {
        "resumed": True,
        "path": "convergence_lease",
        "pipeline_run_id": str(pipeline_run_id),
        "tcre_job_id": str(tcre_job_id),
        "tcre_job_status": tcre_job_status,
        "lease": lease_resume,
        "convergence_resume": hint,
    }


on_tcre_completed_for_convergence_v1 = on_tcre_job_terminal_for_execution_v1
on_tcre_completed_for_execution_v1 = on_tcre_job_terminal_for_execution_v1
