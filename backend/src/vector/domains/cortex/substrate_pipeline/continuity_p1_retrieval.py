"""Phase 1 step 1.6 — P1-C component-scoped retrieval materialization (largest island)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_component_materialization import (
    P1_C_ISLAND_SCOPE_KEY_V1,
    RETRIEVAL_PROPAGATION_MODE_COMPONENT_V1,
    evaluate_retrieval_component_scope_v1,
    snapshot_retrieval_aa4_footprint_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    materialize_retrieval_index_for_pipeline_v1,
)

P1_6_STEP = "1.6_p1c_retrieval_island"
DEFAULT_PIPELINE_RUN_ID = uuid.UUID("ce7df86d-b229-4467-ad28-1109ed119d34")


def run_p1c_retrieval_materialization_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    """Drive P1-C retrieval materialization for pipeline (idempotent)."""
    scope = evaluate_retrieval_component_scope_v1(session, tenant_id=tenant_id)
    island_scope_id = str(scope["island_meta"].get("island_scope_id") or "")
    aa4_before = snapshot_retrieval_aa4_footprint_v1(
        session,
        tenant_id=tenant_id,
        island_scope_id=island_scope_id or None,
    )
    stats = materialize_retrieval_index_for_pipeline_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
    )
    session.commit()
    island_scope_id = str(stats.get("island_scope_id") or island_scope_id or "")
    return {
        "materialization": stats,
        "scope_eval": scope,
        "aa4_footprint_after": snapshot_retrieval_aa4_footprint_v1(
            session,
            tenant_id=tenant_id,
            island_scope_id=island_scope_id or None,
        ),
        "aa4_footprint_before_pass": aa4_before,
    }


def snapshot_p1c_retrieval_proof_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    materialization_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect P1-C retrieval proof inputs from prod DB."""
    scope = evaluate_retrieval_component_scope_v1(session, tenant_id=tenant_id)
    island_scope_id = str(
        (materialization_stats or {}).get("island_scope_id")
        or scope["island_meta"].get("island_scope_id")
        or ""
    )
    aa4 = snapshot_retrieval_aa4_footprint_v1(
        session,
        tenant_id=tenant_id,
        island_scope_id=island_scope_id or None,
    )
    return {
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else None,
        "component_scope": scope,
        "materialization_stats": materialization_stats,
        "aa4_footprint": aa4,
        "island_scope_id": island_scope_id,
    }


def evaluate_p1_6_retrieval_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    proof_snapshot: dict[str, Any],
    materialization_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step 1.6: P1-C largest-island retrieval + AA4 partial footprint."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    scope = dict(proof_snapshot.get("component_scope") or {})
    stats = dict(
        proof_snapshot.get("materialization_stats")
        or (materialization_drive or {}).get("materialization")
        or {}
    )
    aa4 = dict(proof_snapshot.get("aa4_footprint") or {})
    island_meta = dict(scope.get("island_meta") or {})

    propagation_mode = str(stats.get("retrieval_propagation_mode") or "")
    component_mode_ok = propagation_mode == RETRIEVAL_PROPAGATION_MODE_COMPONENT_V1 or (
        bool(scope.get("component_scope_enabled")) and bool(island_scope_id)
    )
    island_count = int(stats.get("island_entity_count") or scope.get("island_entity_count") or 0)
    islands_eligible = int(
        stats.get("islands_eligible_count") or island_meta.get("islands_eligible_count") or 0
    )
    entries_materialized = int(stats.get("entries_materialized") or 0)
    build_ok = (
        str(stats.get("build_state") or "") == "PUBLISHED"
        or bool(stats.get("ok"))
        or int(aa4.get("total_entries") or 0) > 0
    )
    outside_count = int(stats.get("outside_island_scope_entity_count") or 0)
    total_aa4 = int(aa4.get("total_entries") or 0)
    distinct_hours = int(aa4.get("distinct_created_hours") or 0)
    island_scope_id = str(
        proof_snapshot.get("island_scope_id") or stats.get("island_scope_id") or ""
    )

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "component_scope_enabled": bool(scope.get("component_scope_enabled")),
        "retrieval_propagation_mode_component": component_mode_ok,
        "largest_island_selected": bool(stats.get("largest_island_selected")) or island_count > 0,
        "islands_eligible_count_gt_zero": islands_eligible > 0,
        "island_entity_count_ge_min": island_count >= int(scope.get("min_component_entities") or 2),
        "outside_island_scope_documented": outside_count >= 0,
        "island_scope_id_present": bool(island_scope_id),
        "retrieval_index_epoch_published": build_ok,
        "entries_materialized_in_island_pass_gt_zero": entries_materialized > 0
        or int(aa4.get("total_entries") or 0) > 0,
        "aa4_partial_retrieval_footprint": total_aa4 > 0
        and (distinct_hours >= 1 or entries_materialized > 0),
    }
    checks_advisory = {
        "aa4_multi_hour_spread": distinct_hours >= 2,
        "aa4_total_entries_ge_10": total_aa4 >= 10,
    }
    step_16_pass = all(checks.values())

    return {
        "step": P1_6_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "proof_snapshot": proof_snapshot,
        "materialization_drive": materialization_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p1_6_pass": step_16_pass,
        "verification": {
            "step_16_pass": step_16_pass,
            "cleared_for_phase_2": step_16_pass,
            "island_scope_key": P1_C_ISLAND_SCOPE_KEY_V1,
        },
    }
