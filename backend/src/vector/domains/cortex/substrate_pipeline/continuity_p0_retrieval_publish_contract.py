"""Phase B step B1 — single publish contract for retrieval materialization (R-REC-1)."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_publish_contract import (
    P0_B1_STEP,
    RETRIEVAL_PUBLISH_CONTRACT_SCHEMA_VERSION,
    audit_published_epoch_entry_alignment_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL
from vector.infrastructure.db.models.cortex_retrieval_index_epoch import CortexRetrievalIndexEpoch
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePhaseRun

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")
PHASE_B_RETRIEVAL_PUBLISH_CONTRACT_SCHEMA_VERSION = RETRIEVAL_PUBLISH_CONTRACT_SCHEMA_VERSION


def verify_b1_retrieval_publish_contract_wiring_v1() -> dict[str, Any]:
    """Static wiring: one BUILDING epoch, deferred publish, single finalize barrier."""
    errors: list[str] = []
    from vector.domains.cortex.retrieval import retrieval_component_materialization as comp_mod
    from vector.domains.cortex.retrieval import retrieval_index_materialization as mat_mod
    from vector.domains.cortex.retrieval import retrieval_publish_contract as contract_mod
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    comp_src = inspect.getsource(comp_mod.materialize_retrieval_index_for_largest_island_v1)
    for needle in (
        "begin_pipeline_retrieval_index_build_v1",
        "finalize_pipeline_retrieval_index_build_v1",
        "auto_publish=False",
    ):
        if needle not in comp_src:
            errors.append(f"component_mat_missing_{needle}")
    if "publish_retrieval_index_epoch_v1(" in comp_src:
        errors.append("component_mat_direct_publish_call")

    mat_src = inspect.getsource(mat_mod.materialize_retrieval_index_for_pipeline_v1)
    if "is_retrieval_component_scope_enabled_v1()" in mat_src:
        pass
    else:
        errors.append("pipeline_mat_missing_component_dispatch")
    # Non-component branch lives in same function after early return.
    mat_fn = mat_mod.materialize_retrieval_index_for_pipeline_v1
    full_src = inspect.getsource(mat_fn)
    if "begin_pipeline_retrieval_index_build_v1" not in full_src:
        errors.append("pipeline_mat_missing_begin_build")
    if "finalize_pipeline_retrieval_index_build_v1" not in full_src:
        errors.append("pipeline_mat_missing_finalize_build")

    entry_src = inspect.getsource(mat_mod.materialize_retrieval_index_entry_v1)
    if 'build_state != "BUILDING"' not in entry_src:
        errors.append("entry_mat_missing_building_auto_publish_guard")

    p07_src = inspect.getsource(pr_mod.run_phase_07_retrieval_v1)
    if "materialize_retrieval_index_for_pipeline_v1" not in p07_src:
        errors.append("phase_07_missing_pipeline_materialize")
    if "get_published_index_epoch_v1" not in p07_src:
        errors.append("phase_07_missing_published_epoch_attachment")

    contract_src = inspect.getsource(contract_mod.finalize_pipeline_retrieval_index_build_v1)
    if "publish_retrieval_index_epoch_v1" not in contract_src:
        errors.append("contract_finalize_missing_publish")
    if "audit_published_epoch_entry_alignment_v1" not in contract_src:
        errors.append("contract_finalize_missing_audit")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "publish_contract_schema_version": PHASE_B_RETRIEVAL_PUBLISH_CONTRACT_SCHEMA_VERSION,
    }


def snapshot_retrieval_publish_contract_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Prod snapshot: published epoch alignment + inflight BUILDING epochs."""
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        get_published_index_epoch_v1,
    )

    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    audit: dict[str, Any] | None = None
    if published:
        audit = audit_published_epoch_entry_alignment_v1(
            session,
            tenant_id=tenant_id,
            index_epoch=published,
        )

    building_rows = list(
        session.scalars(
            select(CortexRetrievalIndexEpoch).where(
                CortexRetrievalIndexEpoch.tenant_id == tenant_id,
                CortexRetrievalIndexEpoch.build_state == "BUILDING",
            )
        ).all()
    )

    latest_p07 = session.scalar(
        select(CortexSubstratePhaseRun)
        .where(
            CortexSubstratePhaseRun.tenant_id == tenant_id,
            CortexSubstratePhaseRun.phase_id == PHASE_07_RETRIEVAL,
        )
        .order_by(CortexSubstratePhaseRun.completed_at.desc().nullslast())
        .limit(1)
    )
    p07_raw: dict[str, Any] = {}
    if latest_p07 is not None and isinstance(latest_p07.output_json, dict):
        p07_raw = latest_p07.output_json

    return {
        "tenant_id": str(tenant_id),
        "published_index_epoch": published,
        "publish_contract_audit": audit,
        "building_epochs_inflight": len(building_rows),
        "building_epoch_names": [r.index_epoch for r in building_rows[:5]],
        "latest_phase_07_has_publish_contract_audit": "publish_contract_audit" in p07_raw,
        "latest_phase_07_published_index_epoch": p07_raw.get("published_index_epoch"),
        "wiring": verify_b1_retrieval_publish_contract_wiring_v1(),
        "phase_b_retrieval_publish_contract_schema_version": (
            PHASE_B_RETRIEVAL_PUBLISH_CONTRACT_SCHEMA_VERSION
        ),
    }


def evaluate_p0_b1_retrieval_publish_contract_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step B1: R-REC-1 publish barrier wired; published epoch entry alignment when rows exist."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    audit = dict(snapshot.get("publish_contract_audit") or {})
    entries_in_epoch = int(audit.get("entries_in_materialized_epoch") or 0)
    epochs_align = bool(audit.get("epochs_align"))
    build_state = audit.get("build_state")
    inflight_building = int(snapshot.get("building_epochs_inflight") or 0)

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "publish_contract_schema_version": int(
            snapshot.get("phase_b_retrieval_publish_contract_schema_version") or 0
        )
        >= PHASE_B_RETRIEVAL_PUBLISH_CONTRACT_SCHEMA_VERSION,
        "published_epoch_row_present": bool(snapshot.get("published_index_epoch")),
        "no_inflight_building_epochs": inflight_building == 0,
        "published_epoch_entries_align": epochs_align or entries_in_epoch == 0,
        "published_epoch_build_state": build_state == "PUBLISHED" or entries_in_epoch == 0,
    }
    checks_advisory = {
        "published_index_epoch": snapshot.get("published_index_epoch"),
        "entries_in_materialized_epoch": entries_in_epoch,
        "entries_with_island_scope_in_epoch": audit.get("entries_with_island_scope_in_epoch"),
        "building_epochs_inflight": inflight_building,
        "latest_phase_07_has_publish_contract_audit": snapshot.get(
            "latest_phase_07_has_publish_contract_audit"
        ),
        "sql_epoch_alignment": audit,
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_b1_pass = all(checks.values())
    return {
        "step": P0_B1_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_b1_pass": p0_b1_pass,
        "verification": {
            "step_b1_pass": p0_b1_pass,
            "cleared_for_b2": p0_b1_pass,
        },
    }
