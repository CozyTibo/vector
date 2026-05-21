"""M8 admin execution commands — inspect, restart, clear, rerun (engine-only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.admin_rerun import admin_rerun_substrate_execution_v1
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.execution.progression_status import build_substrate_progression_status_v1
from vector.domains.cortex.execution.tenant_constants import FSM_BLOCKED, LEASE_STATUS_RUNNING
from vector.domains.cortex.ingestion.full_pipeline_reset import (
    clear_derived_outputs_from_phase_v1,
    flush_tenant_cortex_pipeline_state,
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

_FROM_PHASE_TO_CURSOR: dict[str, str] = {
    "CANONICAL": PHASE_02_CANONICAL,
    "CANONICAL_DRAINING": PHASE_02_CANONICAL,
    "IDENTITY": PHASE_03_IDENTITY,
    "GRAPH": PHASE_04_GRAPH,
    "TRAVERSAL": PHASE_05_TRAVERSAL,
    "AWAITING_TCRE": PHASE_06_TCRE,
    "TCRE": PHASE_06_TCRE,
    "RETRIEVAL": PHASE_07_RETRIEVAL,
    "SYNTHESIS": PHASE_08_SYNTHESIS,
}


def resolve_phase_cursor_v1(from_phase: str) -> str:
    key = (from_phase or "").strip().upper()
    cursor = _FROM_PHASE_TO_CURSOR.get(key)
    if cursor is None:
        msg = f"unsupported_from_phase:{from_phase}"
        raise ValueError(msg)
    return cursor


def build_execution_inspect_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    transition_limit: int = 50,
) -> dict[str, Any]:
    """Read-only execution state: lease, progression snapshot, recent transitions."""
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    progression = build_substrate_progression_status_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
    )
    lim = max(1, min(int(transition_limit), 200))
    transitions = list(
        session.scalars(
            select(CortexExecutionTransitionLog)
            .where(CortexExecutionTransitionLog.tenant_id == tenant_id)
            .order_by(CortexExecutionTransitionLog.created_at.desc())
            .limit(lim)
        ).all()
    )
    return {
        "surface_kind": "execution_inspect",
        "tenant_id": str(tenant_id),
        "lease": (
            {
                "status": lease.status,
                "fsm_state": lease.fsm_state,
                "phase_cursor": lease.phase_cursor,
                "obligation_epoch": int(lease.obligation_epoch),
                "target_epoch": int(lease.target_epoch),
                "pipeline_run_id": str(lease.pipeline_run_id) if lease.pipeline_run_id else None,
                "block_reason_code": lease.block_reason_code,
                "block_detail": lease.block_detail,
            }
            if lease is not None
            else None
        ),
        "progression": progression,
        "transitions": [
            {
                "from_state": row.from_state,
                "to_state": row.to_state,
                "trigger": row.trigger,
                "gate_result": row.gate_result,
                "receipt_hash": row.receipt_hash,
                "pipeline_run_id": str(row.pipeline_run_id) if row.pipeline_run_id else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "detail_json": dict(row.detail_json or {}),
            }
            for row in transitions
        ],
    }


def restart_execution_from_phase_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    from_phase: str,
    pipeline_run_id: uuid.UUID | None = None,
    force: bool = False,
    break_glass: bool = False,
) -> dict[str, Any]:
    """Set cursor at ``from_phase``, mark dirty, enqueue execution slice."""
    if not break_glass:
        row = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
        now = datetime.now(UTC)
        if (
            row is not None
            and row.status == LEASE_STATUS_RUNNING
            and row.lease_expires_at is not None
            and row.lease_expires_at > now
        ):
            return {
                "restarted": False,
                "reason": "lease_held_by_other_worker",
                "hint": "retry with break_glass=true after worker completes",
            }

    phase_cursor = resolve_phase_cursor_v1(from_phase)
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    blocked = lease is not None and (lease.fsm_state or "").strip() == FSM_BLOCKED
    if blocked and not force and not break_glass:
        return {
            "restarted": False,
            "reason": "execution_blocked",
            "block_reason_code": lease.block_reason_code if lease else None,
            "hint": "use force=true after fixing upstream",
        }

    return admin_rerun_substrate_execution_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_cursor=phase_cursor,
        force=force or break_glass,
    )


def run_canonical_determinism_repair_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str | None = None,
    scan_limit: int = 5000,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Operator determinism repair — not on substrate execution hot path .

    Prefer this or ``POST .../cortex/canonical/verification/repair-determinism-drift`` over
    phase 02 inline repair.
    """
    from vector.domains.cortex.canonical.transform_runtime import (
        repair_tenant_materialization_oracle_determinism_drift,
        resolve_default_bundle_id_for_stub_transform,
    )

    bid = (bundle_id or "").strip() or resolve_default_bundle_id_for_stub_transform(
        session, tenant_id
    )
    if not bid:
        return {"skipped": True, "reason": "no_transformable_bundle"}
    return repair_tenant_materialization_oracle_determinism_drift(
        session,
        tenant_id=tenant_id,
        bundle_id=bid,
        scan_limit=max(1, min(int(scan_limit), 5000)),
        dry_run=dry_run,
    )


def clear_derived_execution_outputs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    from_phase: str,
    scope: str | None = None,
    flush_all: bool = False,
) -> dict[str, Any]:
    """Clear derived substrate outputs from phase (or full tenant flush when ``flush_all``)."""
    if flush_all:
        return flush_tenant_cortex_pipeline_state(session, tenant_id=tenant_id)
    return clear_derived_outputs_from_phase_v1(
        session,
        tenant_id=tenant_id,
        from_phase=from_phase,
        scope=scope,
    )


def execution_rerun_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    from_phase: str,
    pipeline_run_id: uuid.UUID | None = None,
    scope: str | None = None,
    force: bool = False,
    break_glass: bool = False,
    flush_all: bool = False,
    run_determinism_repair: bool = False,
) -> dict[str, Any]:
    """Atomic clear + restart (replay contract §4.1)."""
    determinism_repair: dict[str, Any] | None = None
    if run_determinism_repair and not flush_all:
        determinism_repair = run_canonical_determinism_repair_v1(session, tenant_id=tenant_id)
    cleared = clear_derived_execution_outputs_v1(
        session,
        tenant_id=tenant_id,
        from_phase=from_phase,
        scope=scope,
        flush_all=flush_all,
    )
    restarted = restart_execution_from_phase_v1(
        session,
        tenant_id=tenant_id,
        from_phase=from_phase,
        pipeline_run_id=pipeline_run_id,
        force=force,
        break_glass=break_glass,
    )
    return {
        "surface_kind": "execution_rerun",
        "tenant_id": str(tenant_id),
        "from_phase": (from_phase or "").strip().upper(),
        "cleared": cleared,
        "restarted": restarted,
        "determinism_repair": determinism_repair,
    }
