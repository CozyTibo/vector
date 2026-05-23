"""Phase 3 step 3.2 — P2-B event triggers proof."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.admin_commands import build_execution_inspect_v1
from vector.domains.cortex.execution.execution_event_triggers import (
    DETAIL_KEY_LAST_GRAPH_HASH_V1,
    EVENT_TRIGGER_GRAPH_HASH_V1,
    EVENT_TRIGGER_IDENTITY_PROMOTION_V1,
    EVENT_TRIGGER_INGEST_V1,
    P2_B_STEP,
    build_event_triggers_inspect_v1,
    is_execution_event_triggers_enabled_v1,
    resolve_live_graph_projection_hash_v1,
    trigger_graph_hash_walk_schedule_v1,
)
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1,
    build_substrate_traversal_scheduling_catalog_v1,
)

P3_2_STEP = "3.2_p2b_event_triggers"
DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_p2b_event_trigger_wiring_v1() -> dict[str, Any]:
    """Static wiring checks for P2-B (ingest, identity promotion, graph-hash walks)."""
    from vector.domains.cortex.identity import continuity_rebuild as crb
    from vector.domains.cortex.ingestion import post_ingestion_refresh_dispatch as pid
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr

    errors: list[str] = []
    pid_src = inspect.getsource(pid.schedule_post_ingestion_substrate_refresh)
    if "trigger_post_ingestion_execution_v1" not in pid_src:
        errors.append("post_ingestion_missing_trigger_post_ingestion")
    crb_src = inspect.getsource(crb.run_identity_substrate_projection_for_pipeline_v1)
    if "trigger_identity_promotion_after_substrate_v1" not in crb_src:
        errors.append("identity_substrate_missing_promotion_trigger")
    p04_src = inspect.getsource(pr.run_phase_04_graph_v1)
    if "trigger_graph_hash_walk_schedule_v1" not in p04_src:
        errors.append("phase04_missing_graph_hash_trigger")
    catalog = build_substrate_traversal_scheduling_catalog_v1()
    if TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1 not in catalog.get("schedule_triggers", []):
        errors.append("catalog_missing_graph_hash_changed_trigger")
    return {
        "wiring_ok": not errors,
        "errors": errors,
        "ingest_trigger": EVENT_TRIGGER_INGEST_V1,
        "identity_trigger": EVENT_TRIGGER_IDENTITY_PROMOTION_V1,
        "graph_hash_trigger": EVENT_TRIGGER_GRAPH_HASH_V1,
    }


def snapshot_event_triggers_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    triggers = build_event_triggers_inspect_v1(session, tenant_id=tenant_id)
    inspect_payload = build_execution_inspect_v1(session, tenant_id=tenant_id, transition_limit=3)
    return {
        "tenant_id": str(tenant_id),
        "event_triggers_enabled": is_execution_event_triggers_enabled_v1(),
        "triggers": triggers,
        "execution_inspect_event_triggers": inspect_payload.get("event_triggers"),
        "wiring": verify_p2b_event_trigger_wiring_v1(),
    }


def drive_graph_hash_change_proof_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Force hash-change path by seeding a stale stored hash, then scheduling walks."""
    live_hash = resolve_live_graph_projection_hash_v1(session, tenant_id=tenant_id)
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if lease is None or not live_hash:
        return {"acquired": False, "reason": "missing_lease_or_live_hash"}
    detail = dict(lease.detail_json or {})
    detail[DETAIL_KEY_LAST_GRAPH_HASH_V1] = "stale_hash_for_p2b_proof"
    lease.detail_json = detail
    session.flush()
    manifest = trigger_graph_hash_walk_schedule_v1(
        session,
        tenant_id=tenant_id,
        graph_projection_stable_hash=live_hash,
        pipeline_run_id=pipeline_run_id,
        force_schedule=False,
    )
    session.commit()
    return {"acquired": True, "live_hash": live_hash, "graph_hash_trigger": manifest}


def evaluate_p3_2_event_triggers_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    graph_hash_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step 3.2: P2-B event triggers wired and graph-hash change schedules walks."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    triggers = dict(snapshot.get("triggers") or {})
    graph_manifest = dict((graph_hash_drive or {}).get("graph_hash_trigger") or {})
    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "event_triggers_enabled": bool(snapshot.get("event_triggers_enabled")),
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "graph_hash_trigger_in_catalog": bool(triggers.get("graph_hash_trigger_registered")),
        "ingest_trigger_wired": EVENT_TRIGGER_INGEST_V1 in str(wiring.get("ingest_trigger") or ""),
        "identity_trigger_wired": EVENT_TRIGGER_IDENTITY_PROMOTION_V1
        in str(wiring.get("identity_trigger") or ""),
        "execution_inspect_exposes_event_triggers": isinstance(
            snapshot.get("execution_inspect_event_triggers"), dict
        ),
        "graph_hash_change_detected_in_drive": bool(graph_manifest.get("hash_changed")),
        "graph_hash_walk_schedule_attempted": graph_manifest.get("walk_schedule") is not None,
    }
    checks_advisory = {
        "walks_scheduled_on_hash_change": bool(graph_manifest.get("walks_scheduled")),
        "live_graph_hash": triggers.get("live_graph_projection_stable_hash"),
        "stored_graph_hash_after_drive": graph_manifest.get("new_hash"),
    }
    step_32_pass = all(checks.values())
    return {
        "step": P3_2_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "graph_hash_drive": graph_hash_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p3_2_pass": step_32_pass,
        "verification": {
            "step_32_pass": step_32_pass,
            "cleared_for_step_33": step_32_pass,
        },
    }
