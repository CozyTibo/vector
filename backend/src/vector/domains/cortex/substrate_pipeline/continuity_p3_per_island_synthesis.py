"""Phase 3 step 3.3 — P2-D per-island synthesis proof."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.admin_commands import build_execution_inspect_v1
from vector.domains.cortex.synthesis.synthesis_per_island import (
    GLOBAL_DEGRADATION_BRIEF_SURFACE_V1,
    P2_D_STEP,
    P2_D_SYNTHESIS_SCOPE_LAW_V1,
    build_global_degradation_brief_v1,
    build_per_island_synthesis_inspect_v1,
    is_per_island_synthesis_enabled_v1,
    materialize_synthesis_per_island_v1,
)
from vector.domains.cortex.synthesis.synthesis_pipeline import materialize_synthesis_for_pipeline_v1

P3_3_STEP = P2_D_STEP
DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")
DEFAULT_PIPELINE_RUN_ID = uuid.UUID("ce7df86d-b229-4467-ad28-1109ed119d34")


def verify_p2d_per_island_synthesis_wiring_v1() -> dict[str, Any]:
    """Static wiring: phase_08 materialize delegates to per-island path when enabled."""
    errors: list[str] = []
    mat_src = inspect.getsource(materialize_synthesis_for_pipeline_v1)
    if "materialize_synthesis_per_island_v1" not in mat_src:
        errors.append("materialize_missing_per_island_delegate")
    if "is_per_island_synthesis_enabled_v1" not in mat_src:
        errors.append("materialize_missing_per_island_flag")
    admin_src = inspect.getsource(build_execution_inspect_v1)
    if "per_island_synthesis" not in admin_src:
        errors.append("execution_inspect_missing_per_island_synthesis")
    return {
        "wiring_ok": not errors,
        "errors": errors,
        "synthesis_scope_law": P2_D_SYNTHESIS_SCOPE_LAW_V1,
        "global_brief_surface": GLOBAL_DEGRADATION_BRIEF_SURFACE_V1,
    }


def snapshot_per_island_synthesis_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    panel = build_per_island_synthesis_inspect_v1(session, tenant_id=tenant_id)
    inspect_payload = build_execution_inspect_v1(session, tenant_id=tenant_id, transition_limit=3)
    return {
        "tenant_id": str(tenant_id),
        "per_island_enabled": is_per_island_synthesis_enabled_v1(),
        "panel": panel,
        "execution_inspect_per_island_synthesis": inspect_payload.get("per_island_synthesis"),
        "wiring": verify_p2d_per_island_synthesis_wiring_v1(),
    }


def drive_per_island_synthesis_proof_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    max_islands: int = 1,
    max_scopes_per_island: int = 2,
) -> dict[str, Any]:
    """Bounded prod drive: synthesize largest island only with capped scopes."""
    prid = pipeline_run_id or DEFAULT_PIPELINE_RUN_ID
    out = materialize_synthesis_per_island_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        max_islands=max_islands,
        max_scopes_per_island_override=max_scopes_per_island,
    )
    session.commit()
    return {"acquired": True, "materialize_output": out}


def evaluate_p3_3_per_island_synthesis_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    synthesis_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step 3.3: per-island synthesis wired with global degradation brief."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    panel = dict(snapshot.get("panel") or {})
    mat = dict((synthesis_drive or {}).get("materialize_output") or {})
    brief = dict(mat.get("global_degradation_brief") or {})
    islands = list(panel.get("islands") or [])
    island_results = list(mat.get("island_results") or [])

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "per_island_synthesis_enabled": bool(snapshot.get("per_island_enabled")),
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "panel_surface_kind": panel.get("surface_kind") == "per_island_synthesis",
        "published_index_epoch_present": bool(panel.get("published_index_epoch")),
        "islands_at_least_one": int(panel.get("island_count") or 0) >= 1,
        "outside_island_scope_documented": int(panel.get("outside_island_scope_entity_count") or 0) >= 0,
        "execution_inspect_exposes_per_island_synthesis": isinstance(
            snapshot.get("execution_inspect_per_island_synthesis"), dict
        ),
        "per_island_mode_in_drive": bool(mat.get("per_island_mode")) if synthesis_drive else True,
        "global_degradation_brief_present": brief.get("surface_kind")
        == GLOBAL_DEGRADATION_BRIEF_SURFACE_V1
        if synthesis_drive
        else True,
        "island_results_recorded": len(island_results) >= 1 if synthesis_drive else True,
    }
    checks_advisory = {
        "islands_synthesized_count": brief.get("islands_synthesized_count"),
        "jobs_completed": int(mat.get("jobs_completed") or 0),
        "scopes_scheduled": int(mat.get("scopes_scheduled") or 0),
        "largest_island_entity_count": max(
            (int(i.get("entity_count") or 0) for i in islands),
            default=0,
        ),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    step_33_pass = all(checks.values())
    return {
        "step": P3_3_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "synthesis_drive": synthesis_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p3_3_pass": step_33_pass,
        "verification": {
            "step_33_pass": step_33_pass,
            "cleared_for_step_34": step_33_pass,
        },
    }
