"""Phase 2 step 2.1 — P1-F lease dual-lane fields (admin inspect)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.admin_commands import build_execution_inspect_v1
from vector.domains.cortex.execution.dual_lane_lease import (
    DETAIL_KEY_CANONICAL_LANE_V1,
    DETAIL_KEY_EXECUTION_LANE_V1,
    build_dual_lane_inspect_v1,
)
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL

P2_1_STEP = "2.1_p1f_dual_lane_lease"
DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def snapshot_dual_lane_inspect_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Read admin execution inspect + persisted lease detail_json lanes."""
    inspect = build_execution_inspect_v1(session, tenant_id=tenant_id, transition_limit=5)
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    detail = dict(lease.detail_json or {}) if lease is not None else {}
    dual = dict(inspect.get("dual_lane") or {})
    return {
        "tenant_id": str(tenant_id),
        "inspect_surface_kind": inspect.get("surface_kind"),
        "lease_summary": inspect.get("lease"),
        "dual_lane": dual,
        "detail_json_canonical_lane": detail.get(DETAIL_KEY_CANONICAL_LANE_V1),
        "detail_json_execution_lane": detail.get(DETAIL_KEY_EXECUTION_LANE_V1),
        "phase_cursor": lease.phase_cursor if lease else None,
        "fsm_state": lease.fsm_state if lease else None,
        "lease_status": lease.status if lease else None,
    }


def refresh_dual_lane_on_lease_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Force-sync dual-lane fields on prod lease (idempotent)."""
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if lease is None:
        return {"synced": False, "reason": "no_lease"}
    dual = build_dual_lane_inspect_v1(session, tenant_id=tenant_id, lease=lease)
    session.commit()
    return {"synced": True, "dual_lane": dual}


def evaluate_p2_1_dual_lane_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step 2.1: admin inspect exposes canonical + execution lanes."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    dual = dict(snapshot.get("dual_lane") or {})
    canonical = dict(dual.get("canonical_lane") or snapshot.get("detail_json_canonical_lane") or {})
    execution = dict(dual.get("execution_lane") or snapshot.get("detail_json_execution_lane") or {})
    lease_summary = dict(snapshot.get("lease_summary") or {})

    phase_cursor = str(snapshot.get("phase_cursor") or execution.get("phase_cursor") or "")
    topology_decoupled = bool(dual.get("topology_decoupled_from_execution_cursor"))
    canonical_status = str(canonical.get("lane_status") or lease_summary.get("canonical_lane") or "")
    execution_status = str(execution.get("lane_status") or lease_summary.get("execution_lane") or "")

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "dual_lane_enabled": bool(dual.get("dual_lane_enabled", True)),
        "inspect_has_dual_lane_block": bool(dual),
        "canonical_lane_present": bool(canonical.get("lane")),
        "execution_lane_present": bool(execution.get("lane")),
        "canonical_lane_status_set": canonical_status in (
            "HEALTHY",
            "DEGRADED",
            "BLOCKED",
            "WAITING",
            "UNKNOWN",
        ),
        "execution_lane_status_set": execution_status in (
            "HEALTHY",
            "DEGRADED",
            "BLOCKED",
            "WAITING",
            "UNKNOWN",
        ),
        "lease_summary_shows_both_lane_statuses": bool(lease_summary.get("canonical_lane"))
        and bool(lease_summary.get("execution_lane")),
        "detail_json_persists_both_lanes": bool(snapshot.get("detail_json_canonical_lane"))
        and bool(snapshot.get("detail_json_execution_lane")),
        "execution_lane_has_phase_cursor": execution.get("phase_cursor") is not None
        or phase_cursor != "",
    }
    checks_advisory = {
        "topology_decoupled_from_execution_cursor": topology_decoupled,
        "execution_cursor_past_canonical": phase_cursor in (PHASE_07_RETRIEVAL, "phase_08_synthesis")
        or phase_cursor.startswith("phase_0"),
    }
    step_21_pass = all(checks.values())

    return {
        "step": P2_1_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p2_1_pass": step_21_pass,
        "verification": {
            "step_21_pass": step_21_pass,
            "cleared_for_step_22": step_21_pass,
        },
    }
