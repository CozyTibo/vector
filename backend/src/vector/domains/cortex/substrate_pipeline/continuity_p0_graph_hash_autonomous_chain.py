"""Phase B step B5 — graph-hash autonomous chain proof (P2-B → walks → TCRE → 07)."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.graph_hash_autonomous_chain import (
    CHAIN_LINK_RETRIEVAL_V1,
    GRAPH_HASH_AUTONOMOUS_CHAIN_SCHEMA_VERSION,
    P0_B5_STEP,
    find_graph_hash_chain_evidence_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1,
    build_substrate_traversal_scheduling_catalog_v1,
)

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_b5_graph_hash_autonomous_chain_wiring_v1() -> dict[str, Any]:
    """Static wiring: phase 04 graph-hash trigger, dual-lane 04→07, chain runner, no unlock."""
    errors: list[str] = []
    from vector.domains.cortex.execution import dual_lane_worker as dl_mod
    from vector.domains.cortex.execution import execution_event_triggers as et_mod
    from vector.domains.cortex.substrate_pipeline import graph_hash_autonomous_chain as chain_mod
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    p04_src = inspect.getsource(pr_mod.run_phase_04_graph_v1)
    if "trigger_graph_hash_walk_schedule_v1" not in p04_src:
        errors.append("phase_04_missing_graph_hash_trigger")

    dl_src = inspect.getsource(dl_mod._run_execution_lane_slice_v1)
    if "run_phase_04_graph_v1" not in dl_src or "run_phase_07_retrieval_v1" not in dl_src:
        errors.append("dual_lane_missing_04_to_07_chain")

    chain_src = inspect.getsource(chain_mod.run_graph_hash_autonomous_chain_v1)
    for needle in (
        "run_phase_04_graph_v1",
        "run_phase_05_traversal_v1",
        "_execute_phase06_tcre_sync_v1",
        "run_phase_07_retrieval_v1",
        "no_unlock_scripts",
    ):
        if needle not in chain_src:
            errors.append(f"chain_runner_missing_{needle}")
    if "unlock_step" in chain_src:
        errors.append("chain_runner_references_unlock_script")

    catalog = build_substrate_traversal_scheduling_catalog_v1()
    if TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1 not in catalog.get("schedule_triggers", []):
        errors.append("catalog_missing_graph_hash_changed_trigger")

    et_src = inspect.getsource(et_mod.trigger_graph_hash_walk_schedule_v1)
    if "trigger_graph_hash_walk_schedule_v1" not in et_src or "schedule_octs_walks_for_tenant_v1" not in et_src:
        errors.append("graph_hash_trigger_schedule_missing")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "autonomous_chain_schema_version": GRAPH_HASH_AUTONOMOUS_CHAIN_SCHEMA_VERSION,
    }


def snapshot_graph_hash_autonomous_chain_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lookback_hours: int = 168,
) -> dict[str, Any]:
    """Prod snapshot: historical chain evidence + trigger inspect."""
    from vector.domains.cortex.execution.execution_event_triggers import (
        build_event_triggers_inspect_v1,
    )

    evidence = find_graph_hash_chain_evidence_v1(
        session,
        tenant_id=tenant_id,
        lookback_hours=lookback_hours,
    )
    triggers = build_event_triggers_inspect_v1(session, tenant_id=tenant_id)
    complete_chains = [e for e in evidence if e.get("chain_ok")]
    return {
        "tenant_id": str(tenant_id),
        "lookback_hours": lookback_hours,
        "chain_evidence": evidence,
        "complete_chains_in_window": len(complete_chains),
        "latest_complete_chain": complete_chains[0] if complete_chains else None,
        "event_triggers_inspect": triggers,
        "wiring": verify_b5_graph_hash_autonomous_chain_wiring_v1(),
        "autonomous_chain_schema_version": GRAPH_HASH_AUTONOMOUS_CHAIN_SCHEMA_VERSION,
    }


def evaluate_p0_b5_graph_hash_autonomous_chain_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    chain_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step B5: end-to-end autonomous chain without unlock scripts."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    complete_in_window = int(snapshot.get("complete_chains_in_window") or 0)
    latest = dict(snapshot.get("latest_complete_chain") or {})
    drive = dict(chain_drive or {})
    drive_links = dict(drive.get("chain_links") or {})
    drive_ok = bool(drive.get("chain_ok"))

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "autonomous_chain_schema_version": int(
            snapshot.get("autonomous_chain_schema_version") or 0
        )
        >= GRAPH_HASH_AUTONOMOUS_CHAIN_SCHEMA_VERSION,
        "graph_hash_trigger_in_catalog": bool(
            (snapshot.get("event_triggers_inspect") or {}).get("graph_hash_trigger_registered")
        ),
        "event_triggers_enabled": bool(
            (snapshot.get("event_triggers_inspect") or {}).get("event_triggers_enabled")
        ),
        "chain_evidence_in_sql_window": complete_in_window > 0 or drive_ok,
        "chain_drive_ok_when_run": (not drive) or drive_ok,
        "retrieval_link_ok_when_driven": (not drive_links)
        or bool((drive_links.get(CHAIN_LINK_RETRIEVAL_V1) or {}).get("ok")),
    }
    checks_advisory = {
        "complete_chains_in_window": complete_in_window,
        "latest_complete_chain": latest,
        "chain_drive": chain_drive,
        "chain_drive_links": drive_links,
        "live_graph_hash": (snapshot.get("event_triggers_inspect") or {}).get(
            "live_graph_projection_stable_hash"
        ),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_b5_pass = all(checks.values())
    return {
        "step": P0_B5_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "chain_drive": chain_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_b5_pass": p0_b5_pass,
        "verification": {
            "step_b5_pass": p0_b5_pass,
            "cleared_for_b6": p0_b5_pass,
            "b5_autonomous_chain": complete_in_window > 0 or drive_ok,
        },
    }
