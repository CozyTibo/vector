"""FSM BLOCKED transitions for retrieval starvation and retry exhaustion (M7)."""

from __future__ import annotations

import uuid
from typing import Any, Final, Literal

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.fsm import apply_fsm_transition_v1, fsm_state_for_phase_cursor_v1
from vector.domains.cortex.execution.lease import _get_or_create_lease
from vector.domains.cortex.execution.progression_status import (
    BLOCK_REASON_RETRIEVAL_RETRY_EXHAUSTED_V1,
    MAX_RETRIEVAL_MATERIALIZATION_RETRIES_V1,
    classify_retrieval_materialization_outcome_v1,
    increment_retrieval_retry_v1,
    record_execution_receipt_v1,
    retrieval_retry_count_v1,
)
from vector.domains.cortex.execution.tenant_constants import (
    FSM_BLOCKED,
    LEASE_STATUS_RUNNING,
    LEASE_STATUS_STALLED,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_eligible_scopes_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun
from vector.infrastructure.db.models.cortex_tenant_convergence_lease import CortexTenantConvergenceLease

PostPhase07PolicyOutcome = Literal["continue_08", "retry_07", "blocked"]


def mark_tenant_execution_blocked_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    phase_cursor: str,
    block_reason_code: str,
    block_detail: str,
    trigger: str = "retrieval_policy",
) -> dict[str, Any]:
    """Stop autonomous execution until operator admin rerun."""
    row = _get_or_create_lease(session, tenant_id=tenant_id)
    row.pipeline_run_id = pipeline_run_id
    row.phase_cursor = phase_cursor
    if row.status == LEASE_STATUS_RUNNING:
        row.status = LEASE_STATUS_STALLED
    row.lease_expires_at = None
    apply_fsm_transition_v1(
        session,
        lease=row,
        to_state=FSM_BLOCKED,
        trigger=trigger,
        pipeline_run_id=pipeline_run_id,
        gate_result="fail",
        block_reason_code=block_reason_code[:64],
        block_detail=block_detail[:4000],
        detail={"phase_cursor": phase_cursor},
    )
    session.flush()
    return {
        "tenant_id": str(tenant_id),
        "fsm_state": row.fsm_state,
        "block_reason_code": row.block_reason_code,
        "phase_cursor": phase_cursor,
        "pipeline_run_id": str(pipeline_run_id),
    }


def clear_execution_block_for_rerun_v1(
    session: Session,
    *,
    lease: CortexTenantConvergenceLease,
    phase_cursor: str,
    pipeline_run_id: uuid.UUID,
) -> None:
    """Clear BLOCKED on operator-initiated rerun."""
    lease.pipeline_run_id = pipeline_run_id
    lease.phase_cursor = phase_cursor
    lease.block_reason_code = None
    lease.block_detail = None
    apply_fsm_transition_v1(
        session,
        lease=lease,
        to_state=fsm_state_for_phase_cursor_v1(phase_cursor),
        trigger="admin_rerun_clear_block",
        pipeline_run_id=pipeline_run_id,
        gate_result="pass",
    )
    session.flush()


def apply_post_phase07_retrieval_policy_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    phase07_output: dict[str, Any],
) -> PostPhase07PolicyOutcome:
    """Bounded retrieval retries in execution slice; BLOCKED when exhausted."""
    run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
    if run is None:
        return "continue_08"

    classification = str(phase07_output.get("retrieval_card_classification") or "").strip()
    if not classification:
        classification = classify_retrieval_materialization_outcome_v1(
            entries_materialized=int(phase07_output.get("entries_materialized") or 0),
            entry_count=int(phase07_output.get("entry_count") or 0),
            tcre_candidates=int(phase07_output.get("tcre_candidates") or 0),
            walks_candidates=int(phase07_output.get("walks_candidates") or 0),
            org_link_candidates=int(phase07_output.get("org_link_candidates") or 0),
        )

    if classification != "operational_starvation":
        return "continue_08"

    scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
    index_count = int(scope.get("index_row_count") or 0)
    if index_count > 0:
        return "continue_08"

    retries = retrieval_retry_count_v1(run)
    if retries >= MAX_RETRIEVAL_MATERIALIZATION_RETRIES_V1:
        record_execution_receipt_v1(
            session,
            run=run,
            action="retrieval_retry_exhausted",
            outcome="blocked",
            detail={"retries": retries},
        )
        mark_tenant_execution_blocked_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            phase_cursor=PHASE_07_RETRIEVAL,
            block_reason_code=BLOCK_REASON_RETRIEVAL_RETRY_EXHAUSTED_V1,
            block_detail=f"retries={retries} classification={classification}",
            trigger="retrieval_retry_exhausted",
        )
        return "blocked"

    n = increment_retrieval_retry_v1(session, run=run)
    record_execution_receipt_v1(
        session,
        run=run,
        action="retrieval_materialization_retry",
        outcome="retry",
        detail={"retry": n, "classification": classification},
    )
    return "retry_07"
