"""Phase 3 step 3.1 — P2-C execution island registry proof."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.admin_commands import build_execution_inspect_v1
from vector.domains.cortex.operational_runtime.execution_island_registry import (
    build_island_registry_inspect_v1,
    is_execution_island_registry_enabled_v1,
    sync_execution_island_registry_v1,
)

P3_1_STEP = "3.1_p2c_island_registry"
DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def snapshot_island_registry_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    sync: bool = True,
) -> dict[str, Any]:
    """Prod snapshot: registry inspect + execution inspect island block."""
    registry = build_island_registry_inspect_v1(session, tenant_id=tenant_id, sync=sync)
    inspect = build_execution_inspect_v1(session, tenant_id=tenant_id, transition_limit=3)
    return {
        "tenant_id": str(tenant_id),
        "registry_enabled": is_execution_island_registry_enabled_v1(),
        "registry": registry,
        "execution_inspect_island_registry": inspect.get("island_registry"),
    }


def evaluate_p3_1_island_registry_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step 3.1: persisted island registry with component scope metadata."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    registry = dict(snapshot.get("registry") or {})
    propagation = dict(registry.get("traversal_propagation") or {})
    islands = list(registry.get("islands") or [])
    islands_eligible = int(propagation.get("islands_eligible_count") or 0)

    rows_valid = True
    for row in islands:
        if not row.get("island_scope_id"):
            rows_valid = False
            break
        if int(row.get("entity_count") or 0) < 2:
            rows_valid = False
            break
        if int(row.get("authoritative_edge_count") or 0) < 1:
            rows_valid = False
            break
        if not row.get("entity_ids"):
            rows_valid = False
            break

    has_activity = any(
        row.get("last_walk_at") or row.get("last_retrieval_epoch") for row in islands
    )

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "registry_enabled": bool(snapshot.get("registry_enabled")),
        "registry_surface_kind": registry.get("surface_kind") == "execution_island_registry",
        "component_schedule_enabled": bool(registry.get("component_schedule_enabled")),
        "islands_eligible_at_least_one": islands_eligible >= 1,
        "registry_synced": bool((registry.get("sync") or {}).get("synced")),
        "registry_row_count_matches_eligible": len(islands) == islands_eligible
        if islands_eligible > 0
        else len(islands) >= 0,
        "registry_rows_well_formed": rows_valid if islands else islands_eligible == 0,
        "execution_inspect_exposes_island_registry": isinstance(
            snapshot.get("execution_inspect_island_registry"), dict
        ),
    }
    checks_advisory = {
        "islands_with_walk_or_retrieval_epoch": has_activity,
        "largest_island_entity_count": max(
            (int(r.get("entity_count") or 0) for r in islands),
            default=0,
        ),
        "traversal_propagation_mode": propagation.get("traversal_propagation_mode"),
    }
    step_31_pass = all(checks.values())

    return {
        "step": P3_1_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p3_1_pass": step_31_pass,
        "verification": {
            "step_31_pass": step_31_pass,
            "cleared_for_step_32": step_31_pass,
        },
    }
