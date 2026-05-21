"""FSM helpers: phase cursor mapping and transition application."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.tenant_constants import (
    FSM_AWAITING_TCRE,
    FSM_BLOCKED,
    FSM_CANONICAL_DRAINING,
    FSM_GRAPH,
    FSM_IDLE,
    FSM_IDENTITY,
    FSM_RETRIEVAL,
    FSM_STALLED,
    FSM_SYNTHESIS,
    FSM_TRAVERSAL,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
)
from vector.infrastructure.db.models.cortex_execution_transition_log import CortexExecutionTransitionLog
from vector.infrastructure.db.models.cortex_tenant_convergence_lease import CortexTenantConvergenceLease

_PHASE_TO_FSM: dict[str, str] = {
    PHASE_02_CANONICAL: FSM_CANONICAL_DRAINING,
    PHASE_03_IDENTITY: FSM_IDENTITY,
    PHASE_04_GRAPH: FSM_GRAPH,
    PHASE_05_TRAVERSAL: FSM_TRAVERSAL,
    PHASE_06_TCRE: FSM_AWAITING_TCRE,
    PHASE_07_RETRIEVAL: FSM_RETRIEVAL,
    PHASE_08_SYNTHESIS: FSM_SYNTHESIS,
}


def fsm_state_for_phase_cursor_v1(phase_cursor: str | None) -> str:
    """Map substrate phase cursor to FSM state."""
    key = (phase_cursor or "").strip()
    if not key:
        return FSM_CANONICAL_DRAINING
    return _PHASE_TO_FSM.get(key, FSM_CANONICAL_DRAINING)


def _receipt_hash(
    *,
    tenant_id: uuid.UUID,
    from_state: str,
    to_state: str,
    trigger: str,
    pipeline_run_id: uuid.UUID | None,
) -> str:
    payload = {
        "tenant_id": str(tenant_id),
        "from_state": from_state,
        "to_state": to_state,
        "trigger": trigger,
        "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else None,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def record_execution_transition_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    from_state: str,
    to_state: str,
    trigger: str,
    pipeline_run_id: uuid.UUID | None = None,
    gate_result: str | None = None,
    detail: dict[str, Any] | None = None,
) -> CortexExecutionTransitionLog:
    """Append one FSM transition row (append-only audit)."""
    row = CortexExecutionTransitionLog(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        from_state=from_state[:64],
        to_state=to_state[:64],
        trigger=trigger[:128],
        gate_result=gate_result[:32] if gate_result else None,
        receipt_hash=_receipt_hash(
            tenant_id=tenant_id,
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            pipeline_run_id=pipeline_run_id,
        ),
        detail_json=dict(detail or {}),
    )
    session.add(row)
    session.flush()
    return row


def apply_fsm_transition_v1(
    session: Session,
    *,
    lease: CortexTenantConvergenceLease,
    to_state: str,
    trigger: str,
    pipeline_run_id: uuid.UUID | None = None,
    gate_result: str | None = None,
    block_reason_code: str | None = None,
    block_detail: str | None = None,
    detail: dict[str, Any] | None = None,
) -> str:
    """Update lease ``fsm_state`` and append transition log. Returns previous state."""
    from_state = (lease.fsm_state or FSM_IDLE).strip() or FSM_IDLE
    if from_state == to_state and trigger == "heartbeat":
        return from_state
    lease.fsm_state = to_state
    if to_state == FSM_BLOCKED:
        lease.block_reason_code = (block_reason_code or "")[:64] or None
        lease.block_detail = (block_detail or "")[:4000] if block_detail else None
    elif to_state != FSM_BLOCKED:
        lease.block_reason_code = None
        lease.block_detail = None
    record_execution_transition_v1(
        session,
        tenant_id=lease.tenant_id,
        from_state=from_state,
        to_state=to_state,
        trigger=trigger,
        pipeline_run_id=pipeline_run_id or lease.pipeline_run_id,
        gate_result=gate_result,
        detail=detail,
    )
    return from_state
