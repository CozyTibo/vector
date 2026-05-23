"""Phase C step C2 — per-island scope caps + orchestrator fail-loud proof."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_epoch_scope_alignment import (
    FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
)
from vector.domains.cortex.synthesis.synthesis_per_island_scope_cap_gate import (
    PHASE_C2_SCOPE_CAP_SCHEMA_VERSION,
    P0_C2_STEP,
    is_synthesis_per_island_fail_loud_enabled_v1,
    snapshot_primary_island_artifact_stats_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_FAILED,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")
C2_PRIMARY_ISLAND_MIN_ARTIFACTS_48H = 2


def verify_c2_synthesis_scope_caps_wiring_v1() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis import synthesis_per_island as pi_mod
    from vector.domains.cortex.synthesis import synthesis_pipeline as sp_mod

    pi_src = inspect.getsource(pi_mod.materialize_synthesis_per_island_v1)
    for needle in (
        "materialize_capped_island_scopes_v1",
        "resolve_per_island_scope_cap_budget_v1",
        "enforce_per_island_orchestrator_fail_loud_v1",
        "enforce_all_scopes_failed_fail_loud_v1",
        "per_island_scope_cap_audit",
    ):
        if needle not in pi_src:
            errors.append(f"per_island_materialize_missing_{needle}")

    p08_src = inspect.getsource(sp_mod.run_substrate_phase_08_synthesis_v1)
    for needle in (
        "SynthesisPerIslandMaterializeError",
        "fail_phase_with_receipt_v1",
    ):
        if needle not in p08_src:
            errors.append(f"phase_08_runner_missing_{needle}")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "phase_c2_schema_version": PHASE_C2_SCOPE_CAP_SCHEMA_VERSION,
        "fail_loud_enabled": is_synthesis_per_island_fail_loud_enabled_v1(),
    }


def snapshot_c2_synthesis_scope_caps_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lookback_hours: int = 168,
    artifact_lookback_hours: int = 48,
) -> dict[str, Any]:
    from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1

    artifact_stats = snapshot_primary_island_artifact_stats_v1(
        session,
        tenant_id=tenant_id,
        lookback_hours=artifact_lookback_hours,
    )
    cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
    runs = list(
        session.scalars(
            select(CortexSubstratePipelineRun)
            .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
            .order_by(CortexSubstratePipelineRun.created_at.desc())
            .limit(24)
        ).all()
    )
    slice_summaries: list[dict[str, Any]] = []
    slices_with_cap_audit = 0
    slices_with_scopes_overflow = 0
    orchestrator_fail_loud_receipts = 0
    all_scopes_failed_receipts = 0
    jobs_completed_slices = 0
    max_scopes_on_capped_slice = 0

    for run in runs:
        if run.created_at is not None and run.created_at < cutoff:
            continue
        p08 = get_phase_run_v1(session, pipeline_run_id=run.id, phase_id=PHASE_08_SYNTHESIS)
        if p08 is None:
            continue
        raw = dict(p08.output_json or {})
        receipt = dict(raw.get("substrate_phase_receipt") or {})
        outcome = str(receipt.get("outcome") or raw.get("outcome") or "")
        jobs = int(raw.get("jobs_completed") or 0)
        cap_audit = raw.get("per_island_scope_cap_audit")
        if cap_audit:
            slices_with_cap_audit += 1
            max_scopes_on_capped_slice = max(
                max_scopes_on_capped_slice,
                int(raw.get("scopes_scheduled") or 0),
            )
        if raw.get("scopes_overflow"):
            slices_with_scopes_overflow += 1
        err = str(raw.get("error_code") or receipt.get("error") or "")
        if outcome == PHASE_OUTCOME_FAILED and err == "synthesis_orchestrator_fail_loud":
            orchestrator_fail_loud_receipts += 1
        if outcome == PHASE_OUTCOME_FAILED and err == "synthesis_per_island_all_scopes_failed":
            all_scopes_failed_receipts += 1
        if jobs > 0:
            jobs_completed_slices += 1
        slice_summaries.append(
            {
                "pipeline_run_id": str(run.id),
                "completed_at": p08.completed_at.isoformat() if p08.completed_at else None,
                "phase_08_status": p08.status,
                "receipt_outcome": outcome,
                "jobs_completed": jobs,
                "scopes_scheduled": int(raw.get("scopes_scheduled") or 0),
                "scopes_overflow": bool(raw.get("scopes_overflow")),
                "has_per_island_scope_cap_audit": bool(cap_audit),
                "per_island_scope_cap_budget": raw.get("per_island_scope_cap_budget"),
                "error_code": err or None,
            }
        )

    return {
        "tenant_id": str(tenant_id),
        "lookback_hours": lookback_hours,
        "artifact_lookback_hours": artifact_lookback_hours,
        "primary_island_scope_id": FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
        "artifact_stats": artifact_stats,
        "phase_08_slices": slice_summaries,
        "slices_with_cap_audit": slices_with_cap_audit,
        "slices_with_scopes_overflow": slices_with_scopes_overflow,
        "orchestrator_fail_loud_receipts": orchestrator_fail_loud_receipts,
        "all_scopes_failed_receipts": all_scopes_failed_receipts,
        "slices_with_jobs_completed": jobs_completed_slices,
        "max_scopes_on_capped_slice": max_scopes_on_capped_slice,
        "wiring": verify_c2_synthesis_scope_caps_wiring_v1(),
        "phase_c2_schema_version": PHASE_C2_SCOPE_CAP_SCHEMA_VERSION,
    }


def evaluate_p0_c2_synthesis_scope_caps_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    stats = dict(snapshot.get("artifact_stats") or {})
    primary_artifacts = int(stats.get("artifacts_primary_island") or 0)
    primary_artifacts_published = int(stats.get("artifacts_primary_island_published") or 0)
    cap_audit_slices = int(snapshot.get("slices_with_cap_audit") or 0)
    max_scopes_capped = int(snapshot.get("max_scopes_on_capped_slice") or 0)
    jobs_slices = int(snapshot.get("slices_with_jobs_completed") or 0)
    drive = dict(snapshot.get("phase08_drive") or {})
    cap_law_exercised = cap_audit_slices >= 1 and max_scopes_capped >= C2_PRIMARY_ISLAND_MIN_ARTIFACTS_48H
    artifact_velocity_ok = (
        primary_artifacts >= C2_PRIMARY_ISLAND_MIN_ARTIFACTS_48H
        or primary_artifacts_published >= C2_PRIMARY_ISLAND_MIN_ARTIFACTS_48H
    )

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "fail_loud_on_orchestrator_enabled": bool(wiring.get("fail_loud_enabled")),
        "phase_c2_schema_version": int(snapshot.get("phase_c2_schema_version") or 0)
        >= PHASE_C2_SCOPE_CAP_SCHEMA_VERSION,
        "primary_island_synthesis_velocity_48h": artifact_velocity_ok or cap_law_exercised,
        "per_island_scope_cap_law_exercised": cap_law_exercised,
        "recent_phase08_with_cap_audit_or_jobs": cap_audit_slices >= 1 or jobs_slices >= 1,
        "phase08_drive_ok_when_run": (not drive) or bool(drive.get("ok")),
    }
    checks_advisory = {
        "artifacts_primary_island_48h": primary_artifacts,
        "artifacts_primary_island_published_48h": primary_artifacts_published,
        "artifacts_total_48h": stats.get("artifacts_total"),
        "max_scopes_on_capped_slice": max_scopes_capped,
        "cap_law_exercised": cap_law_exercised,
        "artifact_velocity_ok": artifact_velocity_ok,
        "artifacts_published_total": stats.get("artifacts_published_total"),
        "slices_with_cap_audit": cap_audit_slices,
        "slices_with_scopes_overflow": snapshot.get("slices_with_scopes_overflow"),
        "slices_with_jobs_completed": jobs_slices,
        "orchestrator_fail_loud_receipts": snapshot.get("orchestrator_fail_loud_receipts"),
        "phase08_drive": drive,
        "phase_08_slices": snapshot.get("phase_08_slices"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_c2_pass = all(checks.values())
    return {
        "step": P0_C2_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_c2_pass": p0_c2_pass,
        "verification": {
            "step_c2_pass": p0_c2_pass,
            "cleared_for_c5": p0_c2_pass,
            "primary_island_artifact_velocity": artifact_velocity_ok,
            "per_island_cap_law_exercised": cap_law_exercised,
        },
    }
