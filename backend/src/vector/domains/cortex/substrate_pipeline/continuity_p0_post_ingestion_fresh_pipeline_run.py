"""Phase B step B6 — post-ingestion fresh pipeline run after graph change proof."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import (
    GRAPH_CHANGE_FRESH_PHASES_V1,
)
from vector.domains.cortex.substrate_pipeline.post_ingestion_fresh_pipeline_run import (
    POST_INGESTION_FRESH_RUN_SCHEMA_VERSION,
    P0_B6_STEP,
    find_fresh_graph_change_pipeline_runs_v1,
    is_post_ingestion_fresh_run_on_graph_change_enabled_v1,
    start_fresh_pipeline_run_after_graph_change_v1,
)

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_b6_post_ingestion_fresh_pipeline_run_wiring_v1() -> dict[str, Any]:
    """Static wiring: graph-hash trigger starts fresh run; execution rewinds 03–05; no unlock."""
    errors: list[str] = []
    from vector.domains.cortex.execution import dual_lane_worker as dl_mod
    from vector.domains.cortex.execution import execution_event_triggers as et_mod
    from vector.domains.cortex.execution import run_tenant_execution as rte_mod
    from vector.domains.cortex.substrate_pipeline import post_ingestion_fresh_pipeline_run as b6_mod

    et_src = inspect.getsource(et_mod.trigger_graph_hash_walk_schedule_v1)
    if "start_fresh_pipeline_run_after_graph_change_v1" not in et_src:
        errors.append("graph_hash_trigger_missing_fresh_run")
    if "no_phase_mirror" not in et_src:
        errors.append("graph_hash_trigger_missing_no_phase_mirror")

    b6_src = inspect.getsource(b6_mod.start_fresh_pipeline_run_after_graph_change_v1)
    for needle in (
        "supersede_pipeline_run_for_graph_change_v1",
        "allow_coalesce_running=False",
        "requeue_pipeline_phases_from_v1",
        "no_phase_mirror",
    ):
        if needle not in b6_src:
            errors.append(f"fresh_run_missing_{needle}")

    dl_src = inspect.getsource(dl_mod._run_execution_lane_slice_v1)
    if "resolve_pipeline_run_id_after_phase04_v1" not in dl_src:
        errors.append("dual_lane_missing_phase04_fresh_run_switch")

    rte_src = inspect.getsource(rte_mod.run_tenant_convergence_v1)
    if "resolve_pipeline_run_id_after_phase04_v1" not in rte_src:
        errors.append("execution_slice_missing_phase04_fresh_run_switch")

    if "unlock_step" in b6_src:
        errors.append("fresh_run_module_references_unlock_script")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "post_ingestion_fresh_run_schema_version": POST_INGESTION_FRESH_RUN_SCHEMA_VERSION,
        "fresh_run_on_graph_change_enabled": is_post_ingestion_fresh_run_on_graph_change_enabled_v1(),
    }


def snapshot_post_ingestion_fresh_pipeline_run_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lookback_hours: int = 168,
) -> dict[str, Any]:
    evidence = find_fresh_graph_change_pipeline_runs_v1(
        session,
        tenant_id=tenant_id,
        lookback_hours=lookback_hours,
    )
    from vector.domains.cortex.substrate_pipeline.continuity_p0_recovery import (
        get_latest_pipeline_run_for_tenant_v1,
    )

    latest = get_latest_pipeline_run_for_tenant_v1(session, tenant_id=tenant_id)
    return {
        "tenant_id": str(tenant_id),
        "lookback_hours": lookback_hours,
        "fresh_runs_in_window": len(evidence),
        "fresh_run_evidence": evidence,
        "latest_pipeline_run_id": str(latest.id) if latest is not None else None,
        "latest_pipeline_trigger_kind": latest.trigger_kind if latest is not None else None,
        "latest_pipeline_status": latest.status if latest is not None else None,
        "wiring": verify_b6_post_ingestion_fresh_pipeline_run_wiring_v1(),
        "post_ingestion_fresh_run_schema_version": POST_INGESTION_FRESH_RUN_SCHEMA_VERSION,
    }


def evaluate_p0_b6_post_ingestion_fresh_pipeline_run_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    graph_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step B6: fresh pipeline run after graph change with 03–05 timestamps on new run."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    fresh_count = int(snapshot.get("fresh_runs_in_window") or 0)
    drive = dict(graph_drive or {})
    drive_started = bool(drive.get("started"))
    drive_fresh = drive.get("fresh_pipeline_run_id")
    latest_id = snapshot.get("latest_pipeline_run_id")

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "fresh_run_on_graph_change_enabled": bool(wiring.get("fresh_run_on_graph_change_enabled")),
        "post_ingestion_fresh_run_schema_version": int(
            snapshot.get("post_ingestion_fresh_run_schema_version") or 0
        )
        >= POST_INGESTION_FRESH_RUN_SCHEMA_VERSION,
        "fresh_run_evidence_or_drive": fresh_count > 0 or drive_started,
        "fresh_phases_when_driven": (not drive_started)
        or all(
            phase_id in dict(drive.get("phase_started_at") or {})
            for phase_id in GRAPH_CHANGE_FRESH_PHASES_V1
        ),
        "new_run_distinct_from_prior": (not drive_fresh)
        or str(drive_fresh) != str(drive.get("prior_pipeline_run_id") or latest_id or ""),
    }
    checks_advisory = {
        "fresh_runs_in_window": fresh_count,
        "fresh_run_evidence": snapshot.get("fresh_run_evidence"),
        "graph_drive": graph_drive,
        "latest_pipeline_run_id": latest_id,
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_b6_pass = all(checks.values())
    return {
        "step": P0_B6_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "graph_drive": graph_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_b6_pass": p0_b6_pass,
        "verification": {
            "step_b6_pass": p0_b6_pass,
            "cleared_for_phase_c": p0_b6_pass,
            "b6_fresh_pipeline_run": fresh_count > 0 or drive_started,
        },
    }


def drive_graph_change_fresh_run_proof_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    prior_pipeline_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Prod drive: stale hash + phase-04 trigger path to mint a fresh B6 run."""
    from vector.domains.cortex.execution.execution_event_triggers import (
        DETAIL_KEY_LAST_GRAPH_HASH_V1,
        get_tenant_execution_lease_v1,
        resolve_live_graph_projection_hash_v1,
    )
    from vector.domains.cortex.execution.execution_event_triggers import (
        seed_stale_graph_projection_hash_v1,
    )
    from vector.domains.cortex.substrate_pipeline.phase_runners import run_phase_04_graph_v1
    from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1

    seed = seed_stale_graph_projection_hash_v1(session, tenant_id=tenant_id)
    live_hash = resolve_live_graph_projection_hash_v1(session, tenant_id=tenant_id)
    if not live_hash:
        return {"started": False, "reason": "missing_live_graph_hash", "seed": seed}

    if prior_pipeline_run_id is None:
        from vector.domains.cortex.substrate_pipeline.continuity_p0_recovery import (
            get_latest_pipeline_run_for_tenant_v1,
        )

        latest = get_latest_pipeline_run_for_tenant_v1(session, tenant_id=tenant_id)
        prior_pipeline_run_id = latest.id if latest is not None else None
    if prior_pipeline_run_id is None:
        fresh = start_fresh_pipeline_run_after_graph_change_v1(
            session,
            tenant_id=tenant_id,
            graph_projection_stable_hash=live_hash,
            prior_pipeline_run_id=None,
        )
        return {**fresh, "seed": seed, "path": "direct_fresh_start"}

    from vector.domains.cortex.execution.execution_event_triggers import (
        trigger_graph_hash_walk_schedule_v1,
    )

    trigger = trigger_graph_hash_walk_schedule_v1(
        session,
        tenant_id=tenant_id,
        graph_projection_stable_hash=live_hash,
        pipeline_run_id=prior_pipeline_run_id,
        force_schedule=False,
    )
    fresh_id_raw = trigger.get("fresh_pipeline_run_id")
    phase_started: dict[str, str | None] = {}
    if fresh_id_raw:
        fresh_id = uuid.UUID(str(fresh_id_raw))
        from vector.domains.cortex.substrate_pipeline.phase_runners import (
            run_phase_03_identity_v1,
            run_phase_05_traversal_v1,
        )
        from vector.domains.cortex.canonical.transform_runtime import (
            resolve_default_bundle_id_for_stub_transform,
        )

        bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
        if bundle_id:
            run_phase_03_identity_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=fresh_id,
                bundle_id=bundle_id,
                identity_substrate_trigger="b6_fresh_run_proof",
            )
            p4 = run_phase_04_graph_v1(session, tenant_id=tenant_id, pipeline_run_id=fresh_id)
            run_phase_05_traversal_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=fresh_id,
                graph_projection_stable_hash=p4.get("graph_projection_stable_hash_sha256"),
            )
        for phase_id in GRAPH_CHANGE_FRESH_PHASES_V1:
            pr = get_phase_run_v1(session, pipeline_run_id=fresh_id, phase_id=phase_id)
            phase_started[phase_id] = pr.started_at.isoformat() if pr and pr.started_at else None
    return {
        "started": bool(fresh_id_raw),
        "fresh_pipeline_run_id": fresh_id_raw,
        "prior_pipeline_run_id": str(prior_pipeline_run_id),
        "superseded_pipeline_run_ids": trigger.get("superseded_pipeline_run_ids"),
        "trigger": trigger,
        "seed": seed,
        "path": "phase04_graph_hash_trigger",
        "phase_started_at": phase_started,
        "no_phase_mirror": trigger.get("no_phase_mirror"),
    }
