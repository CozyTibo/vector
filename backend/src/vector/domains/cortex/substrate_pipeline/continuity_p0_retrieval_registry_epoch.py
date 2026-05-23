"""Phase B step B3 — island registry ``last_retrieval_epoch`` wired to retrieval publish."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.execution_island_registry import (
    FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
    P0_B3_STEP,
    RETRIEVAL_REGISTRY_PUBLISH_SCHEMA_VERSION_V1,
    audit_registry_published_epoch_alignment_v1,
    record_retrieval_publish_on_island_registry_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_b3_retrieval_registry_epoch_wiring_v1() -> dict[str, Any]:
    """Static wiring: publish-time registry sync; inspect read-only by default."""
    errors: list[str] = []
    from vector.domains.cortex.operational_runtime import execution_island_registry as reg_mod
    from vector.domains.cortex.retrieval import retrieval_publish_contract as contract_mod
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    reg_src = inspect.getsource(reg_mod.record_retrieval_publish_on_island_registry_v1)
    if "sync_execution_island_registry_v1" not in reg_src:
        errors.append("record_publish_missing_registry_sync")
    if "audit_registry_published_epoch_alignment_v1" not in reg_src:
        errors.append("record_publish_missing_epoch_audit")

    resolve_src = inspect.getsource(reg_mod.resolve_last_retrieval_epoch_for_scope_v1)
    if "get_published_index_epoch_v1" not in resolve_src:
        errors.append("resolve_epoch_missing_published_getter")
    if "count_retrieval_entries_in_scope_v1" not in resolve_src:
        errors.append("resolve_epoch_missing_in_scope_count")

    contract_src = inspect.getsource(contract_mod.finalize_pipeline_retrieval_index_build_v1)
    if "record_retrieval_publish_on_island_registry_v1" not in contract_src:
        errors.append("finalize_missing_record_retrieval_publish")

    inspect_sig = inspect.signature(reg_mod.build_island_registry_inspect_v1)
    if inspect_sig.parameters["sync"].default is not False:
        errors.append("inspect_sync_default_not_false")

    p07_src = inspect.getsource(pr_mod.run_phase_07_retrieval_v1)
    if "record_retrieval_publish_on_island_registry_v1" not in p07_src:
        errors.append("phase_07_missing_registry_publish_hook")
    if "island_registry_publish" not in p07_src:
        errors.append("phase_07_missing_registry_publish_receipt_field")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "registry_publish_schema_version": RETRIEVAL_REGISTRY_PUBLISH_SCHEMA_VERSION_V1,
    }


def snapshot_retrieval_registry_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Prod snapshot: published epoch vs persisted registry rows."""
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        get_published_index_epoch_v1,
    )
    from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePhaseRun
    from sqlalchemy import select

    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    audit = audit_registry_published_epoch_alignment_v1(
        session,
        tenant_id=tenant_id,
        published_index_epoch=published,
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
    p07_registry_publish = None
    if latest_p07 is not None and isinstance(latest_p07.output_json, dict):
        p07_registry_publish = latest_p07.output_json.get(
            "island_registry_publish"
        ) or latest_p07.output_json.get("island_registry_sync")
    return {
        "tenant_id": str(tenant_id),
        "published_index_epoch": published,
        "registry_epoch_audit": audit,
        "latest_phase_07_has_registry_publish": p07_registry_publish is not None,
        "fizzer_primary_island_scope_id": FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
        "wiring": verify_b3_retrieval_registry_epoch_wiring_v1(),
        "registry_publish_schema_version": RETRIEVAL_REGISTRY_PUBLISH_SCHEMA_VERSION_V1,
    }


def evaluate_p0_b3_retrieval_registry_epoch_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    registry_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step B3: registry ``last_retrieval_epoch`` matches published index epoch (B-G5)."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    audit = dict(
        (registry_drive or {}).get("registry_epoch_audit")
        or snapshot.get("registry_epoch_audit")
        or {}
    )
    stale = int(audit.get("registry_rows_stale_vs_published") or 0)
    primary_aligned = bool(audit.get("primary_island_epoch_aligned"))
    primary = dict(audit.get("primary_island") or {})
    primary_in_scope = int(primary.get("entries_in_scope_on_published") or 0)

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "registry_publish_schema_version": int(
            snapshot.get("registry_publish_schema_version") or 0
        )
        >= RETRIEVAL_REGISTRY_PUBLISH_SCHEMA_VERSION_V1,
        "published_epoch_present": bool(snapshot.get("published_index_epoch")),
        "registry_no_stale_epochs_vs_published": stale == 0,
        "primary_island_registry_epoch_aligned": primary_aligned,
        "primary_island_in_scope_gt_zero": primary_in_scope > 0,
    }
    checks_advisory = {
        "published_index_epoch": snapshot.get("published_index_epoch"),
        "registry_rows_stale_vs_published": stale,
        "registry_rows_in_scope_and_aligned": audit.get("registry_rows_in_scope_and_aligned"),
        "primary_island": primary,
        "registry_drive": registry_drive,
        "latest_phase_07_has_registry_publish": snapshot.get(
            "latest_phase_07_has_registry_publish"
        ),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_b3_pass = all(checks.values())
    return {
        "step": P0_B3_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "registry_drive": registry_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_b3_pass": p0_b3_pass,
        "verification": {
            "step_b3_pass": p0_b3_pass,
            "cleared_for_b4": p0_b3_pass,
            "b_g5_registry_epoch": primary_aligned and stale == 0,
        },
    }
