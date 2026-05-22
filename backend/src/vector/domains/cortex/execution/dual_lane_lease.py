"""P1-F — dual-lane lease semantics (canonical vs execution) on ``detail_json``."""

from __future__ import annotations

import uuid
from typing import Any, Final, Literal

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.constants import (
    CANONICAL_OUTCOME_TOPOLOGY_WAIT,
)
from vector.domains.cortex.canonical.forward_progress.deferral_store import count_deferrals
from vector.domains.cortex.canonical.forward_progress.metrics import build_forward_progress_metrics
from vector.domains.cortex.canonical.forward_progress.candidate_selection import (
    list_untreated_routable_count_estimate,
)
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.domains.cortex.execution.tenant_constants import (
    FSM_AWAITING_TCRE,
    FSM_BLOCKED,
    FSM_CANONICAL_DRAINING,
    FSM_STALLED,
    LEASE_STATUS_DIRTY,
    LEASE_STATUS_RUNNING,
    LEASE_STATUS_STALLED,
    LEASE_STATUS_WAITING,
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
from vector.infrastructure.db.models.cortex_tenant_convergence_lease import CortexTenantConvergenceLease

LaneStatus = Literal["HEALTHY", "DEGRADED", "BLOCKED", "WAITING", "UNKNOWN"]

DETAIL_KEY_CANONICAL_LANE_V1: Final[str] = "canonical_lane"
DETAIL_KEY_EXECUTION_LANE_V1: Final[str] = "execution_lane"
DETAIL_KEY_DUAL_LANE_SYNCED_AT_V1: Final[str] = "dual_lane_synced_at"

EXECUTION_LANE_PHASES_V1: Final[frozenset[str]] = frozenset(
    {
        PHASE_03_IDENTITY,
        PHASE_04_GRAPH,
        PHASE_05_TRAVERSAL,
        PHASE_06_TCRE,
        PHASE_07_RETRIEVAL,
        PHASE_08_SYNTHESIS,
    }
)


def is_execution_dual_lane_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_execution_dual_lane_enabled)
    except Exception:  # noqa: BLE001
        return True


def is_execution_lane_phase_cursor_v1(phase_cursor: str | None) -> bool:
    return str(phase_cursor or "").strip() in EXECUTION_LANE_PHASES_V1


def should_mark_execution_lane_stalled_v1(
    lease: CortexTenantConvergenceLease | None,
) -> bool:
    """P1-F: topology/canonical spin must not flip lease to STALLED (execution-only)."""
    if not is_execution_dual_lane_enabled_v1():
        return True
    if lease is None:
        return True
    return is_execution_lane_phase_cursor_v1(lease.phase_cursor)


def _classify_canonical_lane_status_v1(
    *,
    fsm_state: str,
    lease_status: str,
    topology_wait: bool,
    last_canonical_outcome: str,
    untreated_estimate: int,
    retry_ready: int,
) -> LaneStatus:
    if lease_status == LEASE_STATUS_STALLED and fsm_state == FSM_STALLED:
        return "DEGRADED"
    if topology_wait or last_canonical_outcome == CANONICAL_OUTCOME_TOPOLOGY_WAIT:
        return "WAITING"
    if fsm_state in (FSM_CANONICAL_DRAINING,) and lease_status in (
        LEASE_STATUS_RUNNING,
        LEASE_STATUS_DIRTY,
    ):
        return "HEALTHY"
    if untreated_estimate > 5000 or retry_ready > 500:
        return "DEGRADED"
    if last_canonical_outcome in ("partial_progress", "topology_wait"):
        return "DEGRADED"
    if untreated_estimate > 0:
        return "HEALTHY"
    return "UNKNOWN"


def _classify_execution_lane_status_v1(
    *,
    fsm_state: str,
    lease_status: str,
    block_reason_code: str | None,
    phase_cursor: str | None,
    waiting_reason: str | None,
) -> LaneStatus:
    if fsm_state == FSM_BLOCKED or block_reason_code:
        return "BLOCKED"
    if lease_status == LEASE_STATUS_WAITING or fsm_state == FSM_AWAITING_TCRE:
        return "WAITING"
    if lease_status == LEASE_STATUS_STALLED:
        return "DEGRADED"
    if lease_status == LEASE_STATUS_RUNNING and is_execution_lane_phase_cursor_v1(phase_cursor):
        return "HEALTHY"
    if phase_cursor and phase_cursor != PHASE_02_CANONICAL:
        return "HEALTHY"
    if lease_status == LEASE_STATUS_DIRTY and is_execution_lane_phase_cursor_v1(phase_cursor):
        return "DEGRADED"
    return "UNKNOWN"


def build_canonical_lane_detail_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lease: CortexTenantConvergenceLease | None,
) -> dict[str, Any]:
    """Canonical lane snapshot — may remain on topology_wait while execution advances."""
    detail = dict(lease.detail_json or {}) if lease is not None else {}
    bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
    untreated = 0
    deferral: dict[str, int] = {}
    topology_wait = False
    if bundle_id:
        untreated = list_untreated_routable_count_estimate(
            session, tenant_id=tenant_id, bundle_id=bundle_id
        )
        deferral = count_deferrals(session, tenant_id=tenant_id, bundle_id=bundle_id)
        topology_wait = int(deferral.get("deferred_waiting_cooldown") or 0) > 0
    metrics = (
        build_forward_progress_metrics(
            session,
            tenant_id=tenant_id,
            bundle_id=bundle_id or "",
            untreated_estimate=untreated,
            deferral_counts=deferral,
            total_succeeded=0,
            elapsed_ms=0,
        )
        if bundle_id
        else {}
    )
    last_outcome = str(detail.get("last_canonical_outcome") or "")
    convergence_health = str(detail.get("convergence_health") or "") or None
    fsm = str(lease.fsm_state or "") if lease else ""
    status = str(lease.status or "") if lease else ""
    lane_status = _classify_canonical_lane_status_v1(
        fsm_state=fsm,
        lease_status=status,
        topology_wait=topology_wait,
        last_canonical_outcome=last_outcome,
        untreated_estimate=untreated,
        retry_ready=int(deferral.get("deferred_retry_ready") or 0),
    )
    return {
        "lane": "canonical",
        "lane_status": lane_status,
        "outcome": last_outcome or None,
        "convergence_health": convergence_health,
        "topology_wait": topology_wait,
        "untreated_routable_estimate": untreated,
        "drainable_estimate": int(
            metrics.get("drainable_routable_estimate")
            or metrics.get("untreated_routable_estimate")
            or untreated
        ),
        "deferral_counts": deferral,
        "phase_cursor_hint": PHASE_02_CANONICAL,
        "fsm_state": fsm or None,
        "lease_status": status or None,
    }


def build_execution_lane_detail_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lease: CortexTenantConvergenceLease | None,
) -> dict[str, Any]:
    """Execution lane snapshot — substrate phases 03–08 (``phase_cursor`` authority)."""
    _ = session  # reserved for future progression joins
    _ = tenant_id
    detail = dict(lease.detail_json or {}) if lease is not None else {}
    phase_cursor = str(lease.phase_cursor or "") if lease else ""
    fsm = str(lease.fsm_state or "") if lease else ""
    status = str(lease.status or "") if lease else ""
    waiting_reason = str(detail.get("waiting_reason") or "") or None
    lane_status = _classify_execution_lane_status_v1(
        fsm_state=fsm,
        lease_status=status,
        block_reason_code=lease.block_reason_code if lease else None,
        phase_cursor=phase_cursor or None,
        waiting_reason=waiting_reason,
    )
    last_receipt: dict[str, Any] = {}
    if detail.get("last_phase_receipt_hash"):
        last_receipt = {
            "receipt_hash": detail.get("last_phase_receipt_hash"),
            "outcome": detail.get("last_phase_outcome"),
            "phase_id": detail.get("last_phase_id"),
            "blocked_reason": detail.get("last_blocked_reason"),
        }
    return {
        "lane": "execution",
        "lane_status": lane_status,
        "phase_cursor": phase_cursor or None,
        "last_phase_receipt": last_receipt or None,
        "last_error": (lease.last_error[:500] if lease and lease.last_error else None),
        "waiting_reason": waiting_reason,
        "block_reason_code": lease.block_reason_code if lease else None,
        "fsm_state": fsm or None,
        "lease_status": status or None,
        "pipeline_run_id": str(lease.pipeline_run_id) if lease and lease.pipeline_run_id else None,
    }


def sync_dual_lane_fields_on_lease_v1(
    session: Session,
    *,
    lease: CortexTenantConvergenceLease,
) -> dict[str, Any]:
    """Persist ``canonical_lane`` + ``execution_lane`` objects on lease ``detail_json``."""
    if not is_execution_dual_lane_enabled_v1():
        return {}
    from datetime import UTC, datetime

    canonical = build_canonical_lane_detail_v1(
        session, tenant_id=lease.tenant_id, lease=lease
    )
    execution = build_execution_lane_detail_v1(
        session, tenant_id=lease.tenant_id, lease=lease
    )
    detail = dict(lease.detail_json or {})
    detail[DETAIL_KEY_CANONICAL_LANE_V1] = canonical
    detail[DETAIL_KEY_EXECUTION_LANE_V1] = execution
    detail[DETAIL_KEY_DUAL_LANE_SYNCED_AT_V1] = datetime.now(UTC).isoformat()
    lease.detail_json = detail
    return {"canonical_lane": canonical, "execution_lane": execution}


def build_dual_lane_inspect_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lease: CortexTenantConvergenceLease | None,
) -> dict[str, Any]:
    """Inspect payload for admin ``/execution/state`` — both lanes always materialized."""
    enabled = is_execution_dual_lane_enabled_v1()
    if lease is None:
        return {
            "dual_lane_enabled": enabled,
            "canonical_lane": None,
            "execution_lane": None,
            "phase_cursor_execution_only": True,
        }
    detail = dict(lease.detail_json or {})
    canonical = detail.get(DETAIL_KEY_CANONICAL_LANE_V1)
    execution = detail.get(DETAIL_KEY_EXECUTION_LANE_V1)
    if not isinstance(canonical, dict) or not isinstance(execution, dict):
        synced = sync_dual_lane_fields_on_lease_v1(session, lease=lease)
        canonical = synced.get("canonical_lane") or build_canonical_lane_detail_v1(
            session, tenant_id=tenant_id, lease=lease
        )
        execution = synced.get("execution_lane") or build_execution_lane_detail_v1(
            session, tenant_id=tenant_id, lease=lease
        )
    return {
        "dual_lane_enabled": enabled,
        "canonical_lane": canonical,
        "execution_lane": execution,
        "phase_cursor_execution_only": is_execution_lane_phase_cursor_v1(lease.phase_cursor)
        or str(lease.phase_cursor or "") == PHASE_02_CANONICAL,
        "topology_decoupled_from_execution_cursor": bool(
            (canonical or {}).get("topology_wait")
            and is_execution_lane_phase_cursor_v1(lease.phase_cursor)
        ),
    }
