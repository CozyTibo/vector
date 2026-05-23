"""Phase B step B2 — retrieval epoch / island scope alignment (R-REC-1 in-scope law)."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_epoch_scope_alignment import (
    FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
    P0_B2_STEP,
    RETRIEVAL_EPOCH_SCOPE_ALIGNMENT_SCHEMA_VERSION,
    drive_primary_island_scope_realign_v1,
    snapshot_retrieval_epoch_scope_alignment_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL, PHASE_08_SYNTHESIS

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_b2_retrieval_epoch_scope_alignment_wiring_v1() -> dict[str, Any]:
    """Static wiring: epoch-change reconcile + omission merge + phase 07/08 in-scope counts."""
    errors: list[str] = []
    from vector.domains.cortex.retrieval import retrieval_component_materialization as comp_mod
    from vector.domains.cortex.retrieval import retrieval_index_materialization as mat_mod
    from vector.domains.cortex.retrieval import retrieval_epoch_scope_alignment as align_mod
    from vector.domains.cortex.synthesis import synthesis_per_island as syn_mod
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    comp_src = inspect.getsource(comp_mod.materialize_retrieval_index_for_largest_island_v1)
    for needle in (
        "reconcile_primary_island_scope_on_epoch_change_v1",
        "retrieval_entries_in_scope",
        "prior_published_index_epoch",
    ):
        if needle not in comp_src:
            errors.append(f"component_mat_missing_{needle}")

    entry_src = inspect.getsource(mat_mod.materialize_retrieval_index_entry_v1)
    if "merged.update(dict(omission_summary))" not in entry_src:
        errors.append("entry_mat_missing_omission_summary_merge_on_existing")

    mat_src = inspect.getsource(mat_mod.materialize_retrieval_index_for_pipeline_v1)
    if "reconcile_primary_island_scope_on_epoch_change_v1" not in mat_src:
        errors.append("pipeline_mat_missing_epoch_scope_reconcile")

    p07_src = inspect.getsource(pr_mod.run_phase_07_retrieval_v1)
    if "retrieval_entries_in_scope" not in p07_src:
        errors.append("phase_07_missing_retrieval_entries_in_scope")

    syn_src = inspect.getsource(syn_mod.materialize_synthesis_per_island_v1)
    if "retrieval_entries_in_scope" not in syn_src:
        errors.append("phase_08_missing_retrieval_entries_in_scope")

    if not hasattr(align_mod, "realign_island_scope_tags_from_prior_epoch_v1"):
        errors.append("alignment_missing_realign_helper")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "epoch_scope_alignment_schema_version": RETRIEVAL_EPOCH_SCOPE_ALIGNMENT_SCHEMA_VERSION,
    }


def snapshot_b2_retrieval_epoch_scope_proof_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    snap = snapshot_retrieval_epoch_scope_alignment_v1(session, tenant_id=tenant_id)
    snap["wiring"] = verify_b2_retrieval_epoch_scope_alignment_wiring_v1()
    from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePhaseRun
    from sqlalchemy import select

    latest_p08 = session.scalar(
        select(CortexSubstratePhaseRun)
        .where(
            CortexSubstratePhaseRun.tenant_id == tenant_id,
            CortexSubstratePhaseRun.phase_id == PHASE_08_SYNTHESIS,
        )
        .order_by(CortexSubstratePhaseRun.completed_at.desc().nullslast())
        .limit(1)
    )
    island_in_scope_p08: int | None = None
    if latest_p08 is not None and isinstance(latest_p08.output_json, dict):
        for block in latest_p08.output_json.get("island_results") or []:
            if (
                str(block.get("island_scope_id") or "")
                == FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1
            ):
                island_in_scope_p08 = int(block.get("retrieval_entries_in_scope") or 0)
                break
    snap["latest_phase_08_primary_island_in_scope"] = island_in_scope_p08
    latest_p07 = session.scalar(
        select(CortexSubstratePhaseRun)
        .where(
            CortexSubstratePhaseRun.tenant_id == tenant_id,
            CortexSubstratePhaseRun.phase_id == PHASE_07_RETRIEVAL,
        )
        .order_by(CortexSubstratePhaseRun.completed_at.desc().nullslast())
        .limit(1)
    )
    p07_in_scope: int | None = None
    if latest_p07 is not None and isinstance(latest_p07.output_json, dict):
        p07_in_scope = latest_p07.output_json.get("retrieval_entries_in_scope")
    snap["latest_phase_07_retrieval_entries_in_scope"] = p07_in_scope
    return snap


def evaluate_p0_b2_retrieval_epoch_scope_alignment_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    realign_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step B2: primary island in-scope entries on published epoch (B-G1/B-G2)."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    primary_scope = str(snapshot.get("primary_island_scope_id") or "")
    fizzer_in_scope = int(snapshot.get("fizzer_primary_in_scope") or 0)
    primary_in_scope = int(snapshot.get("retrieval_entries_in_scope") or 0)
    after_drive = dict(realign_drive or {})
    if after_drive.get("driven"):
        fizzer_in_scope = max(
            fizzer_in_scope, int(after_drive.get("retrieval_entries_in_scope") or 0)
        )
        if primary_scope == FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1:
            primary_in_scope = fizzer_in_scope

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "epoch_scope_alignment_schema_version": int(
            snapshot.get("epoch_scope_alignment_schema_version") or 0
        )
        >= RETRIEVAL_EPOCH_SCOPE_ALIGNMENT_SCHEMA_VERSION,
        "published_epoch_present": bool(snapshot.get("published_index_epoch")),
        "primary_island_scope_resolved": bool(primary_scope),
        "primary_island_entries_in_scope_gt_zero": primary_in_scope > 0,
        "fizzer_primary_island_in_scope_gt_zero": fizzer_in_scope > 0,
    }
    checks_advisory = {
        "primary_island_scope_id": primary_scope,
        "fizzer_primary_island_scope_id": FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
        "retrieval_entries_in_scope": primary_in_scope,
        "fizzer_primary_in_scope": fizzer_in_scope,
        "tagged_entries_on_published_epoch": snapshot.get("tagged_entries_on_published_epoch"),
        "realign_drive": realign_drive,
        "latest_phase_07_retrieval_entries_in_scope": snapshot.get(
            "latest_phase_07_retrieval_entries_in_scope"
        ),
        "latest_phase_08_primary_island_in_scope": snapshot.get(
            "latest_phase_08_primary_island_in_scope"
        ),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_b2_pass = all(checks.values())
    return {
        "step": P0_B2_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "realign_drive": realign_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_b2_pass": p0_b2_pass,
        "verification": {
            "step_b2_pass": p0_b2_pass,
            "cleared_for_b3": p0_b2_pass,
            "b_g1_partial": primary_in_scope > 0,
            "b_g2_primary_island": fizzer_in_scope > 0,
        },
    }
