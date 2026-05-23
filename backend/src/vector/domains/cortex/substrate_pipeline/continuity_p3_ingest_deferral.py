"""Phase 3 step 3.4 — P2-E ingest caps + deferral release monitoring proof."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.admin_commands import build_execution_inspect_v1
from vector.domains.cortex.execution.execution_ingest_deferral_monitoring import (
    P2_E_STEP,
    build_ingest_deferral_inspect_v1,
    is_ingest_deferral_monitoring_enabled_v1,
    snapshot_github_ingest_caps_extended_v1,
)
from vector.domains.cortex.canonical.forward_progress.deferral_store import probe_deferral_releases_v1
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform

P3_4_STEP = P2_E_STEP
DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_p2e_ingest_deferral_wiring_v1() -> dict[str, Any]:
    """Static wiring: canonical drain persists monitor; execution inspect exposes block."""
    from vector.domains.cortex.canonical.forward_progress import drain_runtime as drain_mod

    errors: list[str] = []
    drain_src = inspect.getsource(drain_mod.drain_forward_progress_backlog)
    if "record_deferral_release_monitor_v1" not in drain_src:
        errors.append("drain_runtime_missing_deferral_monitor_record")
    admin_src = inspect.getsource(build_execution_inspect_v1)
    if "ingest_deferral_monitoring" not in admin_src:
        errors.append("execution_inspect_missing_ingest_deferral_monitoring")
    return {"wiring_ok": not errors, "errors": errors}


def snapshot_ingest_deferral_monitoring_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    panel = build_ingest_deferral_inspect_v1(session, tenant_id=tenant_id)
    inspect_payload = build_execution_inspect_v1(session, tenant_id=tenant_id, transition_limit=3)
    caps = snapshot_github_ingest_caps_extended_v1()
    return {
        "tenant_id": str(tenant_id),
        "monitoring_enabled": is_ingest_deferral_monitoring_enabled_v1(),
        "panel": panel,
        "ingest_caps": caps,
        "execution_inspect_ingest_deferral": inspect_payload.get("ingest_deferral_monitoring"),
        "wiring": verify_p2e_ingest_deferral_wiring_v1(),
    }


def drive_deferral_release_probe_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Prod drive: run deferral release probe (idempotent release paths)."""
    bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
    if not bundle_id:
        return {"acquired": False, "reason": "no_bundle_id"}
    probe = probe_deferral_releases_v1(session, tenant_id=tenant_id, bundle_id=bundle_id)
    session.commit()
    return {"acquired": True, "bundle_id": bundle_id, "release_probe": probe}


def evaluate_p3_4_ingest_deferral_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    release_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step 3.4: raised ingest caps documented + deferral release monitoring wired."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    panel = dict(snapshot.get("panel") or {})
    caps = dict(snapshot.get("ingest_caps") or {})
    deferral = dict(panel.get("deferral_release") or {})
    exhaust = dict(panel.get("exhaust_registry") or {})
    probe = dict((release_drive or {}).get("release_probe") or {})

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "monitoring_enabled": bool(snapshot.get("monitoring_enabled")),
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "panel_surface_kind": panel.get("surface_kind") == "ingest_deferral_monitoring",
        "ingest_caps_snapshot_present": bool(caps.get("fix6_caps")),
        "meets_fix6_recommended": bool(caps.get("meets_fix6_recommended")),
        "deferral_counts_present": bool(deferral.get("deferral_counts")),
        "deferral_pressure_sample": isinstance(deferral.get("deferral_pressure"), list),
        "exhaust_registry_honesty": exhaust.get("surface_kind") == "exhaust_registry_honesty",
        "github_exhaust_declared": isinstance(exhaust.get("github"), dict),
        "execution_inspect_exposes_ingest_deferral": isinstance(
            snapshot.get("execution_inspect_ingest_deferral"), dict
        ),
        "release_probe_ran": bool(release_drive.get("acquired")) if release_drive else True,
        "release_probe_has_counts": bool(probe.get("deferral_counts_after"))
        if release_drive
        else True,
    }
    checks_advisory = {
        "deferred_total": int((deferral.get("deferral_counts") or {}).get("deferred_total") or 0),
        "deferred_retry_ready": int(
            (deferral.get("deferral_counts") or {}).get("deferred_retry_ready") or 0
        ),
        "released_total_probe": int(probe.get("released_total") or 0),
        "github_maturity_level": (exhaust.get("github") or {}).get("maturity_level"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    step_34_pass = all(checks.values())
    return {
        "step": P3_4_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "release_drive": release_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p3_4_pass": step_34_pass,
        "verification": {
            "step_34_pass": step_34_pass,
            "cleared_for_phase_4": step_34_pass,
        },
    }
