"""Postgres-authoritative tenant execution lease operations (M5 FSM)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.fsm import (
    apply_fsm_transition_v1,
    fsm_state_for_phase_cursor_v1,
)
from vector.domains.cortex.execution.tenant_constants import (
    FSM_AWAITING_TCRE,
    FSM_BLOCKED,
    FSM_CANONICAL_DRAINING,
    FSM_IDLE,
    FSM_STALLED,
    LEASE_STATUS_DIRTY,
    LEASE_STATUS_IDLE,
    LEASE_STATUS_RUNNING,
    LEASE_STATUS_STALLED,
    LEASE_STATUS_WAITING,
)
from vector.infrastructure.db.models.cortex_tenant_convergence_lease import (
    CortexTenantConvergenceLease,
    CortexTenantExecution,
)
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def get_tenant_execution_lease_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> CortexTenantExecution | None:
    return session.get(CortexTenantConvergenceLease, tenant_id)


# Back-compat alias
get_convergence_lease_v1 = get_tenant_execution_lease_v1


def _get_or_create_lease(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> CortexTenantConvergenceLease:
    row = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if row is not None:
        return row
    row = CortexTenantConvergenceLease(
        tenant_id=tenant_id,
        status=LEASE_STATUS_IDLE,
        fsm_state=FSM_IDLE,
        obligation_epoch=0,
        target_epoch=0,
    )
    session.add(row)
    session.flush()
    return row


def mark_tenant_dirty_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    reason: str = "ingestion",
) -> dict[str, Any]:
    """Bump obligation epoch and mark tenant as needing execution."""
    now = _now()
    row = _get_or_create_lease(session, tenant_id=tenant_id)
    row.obligation_epoch = int(row.obligation_epoch) + 1
    if row.status != LEASE_STATUS_RUNNING:
        row.status = LEASE_STATUS_DIRTY
    row.next_attempt_at = now
    row.last_error = None
    apply_fsm_transition_v1(
        session,
        lease=row,
        to_state=FSM_CANONICAL_DRAINING,
        trigger=f"mark_dirty:{reason[:64]}",
        detail={"reason": reason[:256]},
    )
    detail = dict(row.detail_json or {})
    detail["last_dirty_reason"] = reason[:256]
    detail["last_dirty_at"] = now.isoformat()
    row.detail_json = detail
    row.updated_at = now
    session.flush()
    _LOGGER.info(
        "execution_lease_marked_dirty tenant_id=%s obligation_epoch=%s fsm_state=%s reason=%s",
        tenant_id,
        row.obligation_epoch,
        row.fsm_state,
        reason,
    )
    return {
        "tenant_id": str(tenant_id),
        "status": row.status,
        "fsm_state": row.fsm_state,
        "obligation_epoch": int(row.obligation_epoch),
        "reason": reason,
    }


def mark_tenant_waiting_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    phase_cursor: str,
    waiting_reason: str,
) -> None:
    now = _now()
    row = _get_or_create_lease(session, tenant_id=tenant_id)
    row.status = LEASE_STATUS_WAITING
    row.pipeline_run_id = pipeline_run_id
    row.phase_cursor = phase_cursor
    row.lease_expires_at = None
    row.last_heartbeat_at = now
    row.next_attempt_at = None
    apply_fsm_transition_v1(
        session,
        lease=row,
        to_state=FSM_AWAITING_TCRE,
        trigger="waiting_on_tcre",
        pipeline_run_id=pipeline_run_id,
        detail={"waiting_reason": waiting_reason[:256], "phase_cursor": phase_cursor},
    )
    detail = dict(row.detail_json or {})
    detail["waiting_reason"] = waiting_reason[:256]
    row.detail_json = detail
    row.updated_at = now
    session.flush()


def schedule_convergence_retry_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    phase_cursor: str | None = None,
    delay_seconds: int = 0,
    last_error: str | None = None,
) -> None:
    now = _now()
    row = _get_or_create_lease(session, tenant_id=tenant_id)
    row.status = LEASE_STATUS_DIRTY
    row.lease_expires_at = None
    if phase_cursor is not None:
        row.phase_cursor = phase_cursor
    row.next_attempt_at = now + timedelta(seconds=max(0, int(delay_seconds)))
    row.last_heartbeat_at = now
    if last_error:
        row.last_error = last_error[:4000]
    apply_fsm_transition_v1(
        session,
        lease=row,
        to_state=fsm_state_for_phase_cursor_v1(row.phase_cursor),
        trigger="schedule_retry",
        detail={"delay_seconds": delay_seconds, "phase_cursor": row.phase_cursor},
    )
    row.updated_at = now
    session.flush()


def mark_tenant_stalled_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    error: str,
    retry_delay_seconds: int | None = None,
) -> None:
    cfg = get_settings()
    delay = retry_delay_seconds
    if delay is None:
        delay = max(60, int(cfg.cortex_convergence_stalled_retry_seconds))
    row = _get_or_create_lease(session, tenant_id=tenant_id)
    row.status = LEASE_STATUS_STALLED
    row.last_error = error[:4000]
    row.attempt_count = int(row.attempt_count) + 1
    row.lease_expires_at = None
    row.next_attempt_at = _now() + timedelta(seconds=delay)
    apply_fsm_transition_v1(
        session,
        lease=row,
        to_state=FSM_STALLED,
        trigger="worker_exception",
        detail={"error": error[:500]},
    )
    row.updated_at = _now()
    session.flush()


def try_acquire_convergence_lease_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
) -> tuple[CortexTenantConvergenceLease | None, str]:
    """Acquire running lease for this worker invocation. Returns (lease, block_reason)."""
    cfg = settings or get_settings()
    now = _now()
    ttl = timedelta(seconds=max(60, int(cfg.cortex_convergence_lease_ttl_seconds)))
    row = session.execute(
        select(CortexTenantConvergenceLease)
        .where(CortexTenantConvergenceLease.tenant_id == tenant_id)
        .with_for_update()
    ).scalar_one_or_none()
    if row is None:
        row = CortexTenantConvergenceLease(
            tenant_id=tenant_id,
            status=LEASE_STATUS_IDLE,
            fsm_state=FSM_IDLE,
            obligation_epoch=0,
            target_epoch=0,
        )
        session.add(row)
        session.flush()

    if row.status == LEASE_STATUS_RUNNING:
        if row.lease_expires_at is not None and row.lease_expires_at > now:
            return None, "lease_held_by_other_worker"
        row.status = LEASE_STATUS_DIRTY
        row.last_error = (row.last_error or "")[:2000] or "lease_expired_recovered"
        _LOGGER.warning(
            "execution_lease_expired_recovered tenant_id=%s",
            tenant_id,
        )

    if row.status == LEASE_STATUS_WAITING:
        return None, "waiting_on_async"

    if (row.fsm_state or "").strip() == FSM_BLOCKED:
        code = (row.block_reason_code or "execution_blocked").strip()
        return None, f"execution_blocked:{code}"

    if row.status == LEASE_STATUS_IDLE and int(row.obligation_epoch) <= int(row.target_epoch):
        return None, "nothing_owed"

    if row.status not in (LEASE_STATUS_DIRTY, LEASE_STATUS_STALLED, LEASE_STATUS_IDLE):
        if row.status != LEASE_STATUS_RUNNING:
            return None, f"unexpected_status:{row.status}"

    if int(row.obligation_epoch) <= 0 and row.status == LEASE_STATUS_IDLE:
        return None, "never_dirty"

    row.status = LEASE_STATUS_RUNNING
    row.target_epoch = int(row.obligation_epoch)
    row.lease_expires_at = now + ttl
    row.last_heartbeat_at = now
    row.attempt_count = int(row.attempt_count) + 1
    row.last_error = None
    row.next_attempt_at = None
    apply_fsm_transition_v1(
        session,
        lease=row,
        to_state=fsm_state_for_phase_cursor_v1(row.phase_cursor),
        trigger="acquire_lease",
        pipeline_run_id=row.pipeline_run_id,
    )
    row.updated_at = now
    session.flush()
    return row, ""


try_acquire_execution_lease_v1 = try_acquire_convergence_lease_v1


def touch_convergence_heartbeat_v1(
    session: Session,
    *,
    lease: CortexTenantConvergenceLease,
    settings: Settings | None = None,
) -> None:
    cfg = settings or get_settings()
    now = _now()
    ttl = timedelta(seconds=max(60, int(cfg.cortex_convergence_lease_ttl_seconds)))
    lease.last_heartbeat_at = now
    lease.lease_expires_at = now + ttl
    lease.updated_at = now
    session.flush()


def complete_convergence_lease_v1(
    session: Session,
    *,
    lease: CortexTenantConvergenceLease,
    pipeline_run_id: uuid.UUID | None = None,
    phase_cursor: str | None = None,
) -> dict[str, Any]:
    """Release lease after an execution slice; stay dirty if obligation advanced."""
    now = _now()
    if pipeline_run_id is not None:
        lease.pipeline_run_id = pipeline_run_id
    if phase_cursor is not None:
        lease.phase_cursor = phase_cursor
    lease.lease_expires_at = None
    lease.last_heartbeat_at = now
    if int(lease.obligation_epoch) > int(lease.target_epoch):
        lease.status = LEASE_STATUS_DIRTY
        lease.next_attempt_at = now
        apply_fsm_transition_v1(
            session,
            lease=lease,
            to_state=fsm_state_for_phase_cursor_v1(lease.phase_cursor),
            trigger="slice_complete_epoch_behind",
            pipeline_run_id=lease.pipeline_run_id,
        )
        _LOGGER.info(
            "execution_lease_still_dirty tenant_id=%s obligation_epoch=%s target_epoch=%s",
            lease.tenant_id,
            lease.obligation_epoch,
            lease.target_epoch,
        )
    else:
        lease.status = LEASE_STATUS_IDLE
        lease.next_attempt_at = None
        apply_fsm_transition_v1(
            session,
            lease=lease,
            to_state=FSM_IDLE,
            trigger="slice_complete",
            pipeline_run_id=lease.pipeline_run_id,
            gate_result="pass",
        )
        _LOGGER.info(
            "execution_lease_idle tenant_id=%s target_epoch=%s",
            lease.tenant_id,
            lease.target_epoch,
        )
    lease.updated_at = now
    session.flush()
    return {
        "tenant_id": str(lease.tenant_id),
        "status": lease.status,
        "fsm_state": lease.fsm_state,
        "obligation_epoch": int(lease.obligation_epoch),
        "target_epoch": int(lease.target_epoch),
    }


complete_execution_lease_v1 = complete_convergence_lease_v1


def list_tenants_for_convergence_sweep_v1(
    session: Session,
    *,
    limit: int,
    settings: Settings | None = None,
) -> list[uuid.UUID]:
    """Tenants that owe execution work now (authoritative scheduler input)."""
    cfg = settings or get_settings()
    now = _now()
    stale_before = now - timedelta(seconds=max(60, int(cfg.cortex_convergence_lease_ttl_seconds)))

    stmt = (
        select(CortexTenantConvergenceLease.tenant_id)
        .where(CortexTenantConvergenceLease.fsm_state != FSM_BLOCKED)
        .where(
            or_(
                (
                    CortexTenantConvergenceLease.status.in_(
                        (LEASE_STATUS_DIRTY, LEASE_STATUS_STALLED)
                    )
                )
                & (
                    (CortexTenantConvergenceLease.next_attempt_at.is_(None))
                    | (CortexTenantConvergenceLease.next_attempt_at <= now)
                ),
                (
                    (CortexTenantConvergenceLease.status == LEASE_STATUS_RUNNING)
                    & (CortexTenantConvergenceLease.lease_expires_at.is_not(None))
                    & (CortexTenantConvergenceLease.lease_expires_at < stale_before)
                ),
            )
        )
        .order_by(CortexTenantConvergenceLease.next_attempt_at.asc().nullsfirst())
        .limit(max(1, min(int(limit), 500)))
    )
    return list(session.execute(stmt).scalars().all())


list_tenants_for_execution_sweep_v1 = list_tenants_for_convergence_sweep_v1


def resume_convergence_from_waiting_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    phase_cursor: str,
) -> dict[str, Any]:
    """After async gap (e.g. TCRE), mark dirty at resume cursor and allow worker pickup."""
    row = _get_or_create_lease(session, tenant_id=tenant_id)
    row.status = LEASE_STATUS_DIRTY
    row.phase_cursor = phase_cursor
    row.next_attempt_at = _now()
    row.lease_expires_at = None
    apply_fsm_transition_v1(
        session,
        lease=row,
        to_state=fsm_state_for_phase_cursor_v1(phase_cursor),
        trigger="resume_from_waiting",
        pipeline_run_id=row.pipeline_run_id,
        detail={"phase_cursor": phase_cursor},
    )
    detail = dict(row.detail_json or {})
    detail["resumed_from_waiting_at"] = _now().isoformat()
    row.detail_json = detail
    row.updated_at = _now()
    session.flush()
    return {
        "tenant_id": str(tenant_id),
        "status": row.status,
        "fsm_state": row.fsm_state,
        "phase_cursor": phase_cursor,
    }
