"""Phase C step C3 — unified audit snapshot proof evaluator."""

from __future__ import annotations

import inspect
from datetime import datetime
from pathlib import Path
from typing import Any

from vector.domains.cortex.substrate_pipeline.continuity_audit_snapshot import (
    AUDIT_SNAPSHOT_SURFACE_KIND,
    PHASE_C3_AUDIT_SNAPSHOT_SCHEMA_VERSION,
    P0_C3_STEP,
    build_continuity_audit_snapshot_v1,
    format_continuity_audit_snapshot_text_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_deprecation import (
    CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1,
    DEPRECATED_CONTINUITY_PROOF_SCRIPTS_V1,
)


def verify_c3_audit_snapshot_wiring_v1(*, repo_root: Path) -> dict[str, Any]:
    from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
        resolve_backend_scripts_dir_v1,
        resolve_repo_relative_path_v1,
    )

    errors: list[str] = []
    script_path = resolve_backend_scripts_dir_v1(repo_root=repo_root) / CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1
    if not script_path.is_file():
        errors.append("missing_canonical_script")

    mod_src = inspect.getsource(build_continuity_audit_snapshot_v1)
    for needle in (
        "build_continuity_proof_panel_v1",
        "build_substrate_sql_snapshot_v1",
        "snapshot_phase08_empty_scope_truth_v1",
        "snapshot_c2_synthesis_scope_caps_v1",
        "panel_text",
    ):
        if needle not in mod_src:
            errors.append(f"audit_snapshot_missing_{needle}")

    if script_path.is_file():
        script_src = script_path.read_text(encoding="utf-8")
        if "build_continuity_audit_snapshot_v1" not in script_src:
            errors.append("canonical_script_missing_build_call")
        if "format_continuity_audit_snapshot_text_v1" not in script_src:
            errors.append("canonical_script_missing_text_formatter")

    prod_queries = resolve_backend_scripts_dir_v1(repo_root=repo_root) / "prod_substrate_proof_queries.py"
    if prod_queries.is_file():
        pq_src = prod_queries.read_text(encoding="utf-8")
        if "build_substrate_sql_snapshot_v1" not in pq_src:
            errors.append("prod_substrate_queries_not_merged")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "phase_c3_schema_version": PHASE_C3_AUDIT_SNAPSHOT_SCHEMA_VERSION,
        "deprecated_script_count": len(DEPRECATED_CONTINUITY_PROOF_SCRIPTS_V1),
        "canonical_script": CANONICAL_AUDIT_SNAPSHOT_SCRIPT_V1,
    }


def evaluate_p0_c3_audit_snapshot_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    snapshot_text: str,
    wiring: dict[str, Any],
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    panel = dict(snapshot.get("panel") or {})
    panel_summary = dict(panel.get("summary") or {})
    substrate = dict(snapshot.get("substrate_sql") or {})
    phase = dict(snapshot.get("phase_snapshots") or {})
    text_upper = snapshot_text.upper()

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "phase_c3_schema_version": int(snapshot.get("phase_c3_schema_version") or 0)
        >= PHASE_C3_AUDIT_SNAPSHOT_SCHEMA_VERSION,
        "audit_snapshot_surface_kind": snapshot.get("surface_kind") == AUDIT_SNAPSHOT_SURFACE_KIND,
        "panel_embedded": panel.get("surface_kind") == "continuity_proof_panel",
        "panel_text_present": bool(snapshot.get("panel_text")),
        "substrate_sql_embedded": substrate.get("surface_kind") == "continuity_substrate_sql_snapshot",
        "phase_snapshots_c1_c2": (
            "c1_phase08_empty_scope_truth" in phase and "c2_synthesis_scope_caps" in phase
        ),
        "deprecated_scripts_catalogued": len(snapshot.get("deprecated_proof_scripts") or []) >= 10,
        "text_prints_aa_panel": "AA1" in text_upper and "AA7" in text_upper,
        "text_prints_substrate_sql": "SUBSTRATE SQL" in text_upper,
        "unified_command_emits_json_fields": all(
            k in snapshot for k in ("panel", "panel_text", "substrate_sql", "phase_snapshots")
        ),
    }
    checks_advisory = {
        "panel_fail_count": panel_summary.get("fail_count"),
        "m3_autonomously_alive": panel_summary.get("m3_autonomously_alive"),
        "obligation_epoch_gap": substrate.get("obligation_epoch_gap"),
        "obligation_epoch_gap_ok": substrate.get("obligation_epoch_gap_ok"),
        "obligation_epoch_gap_ok_when_lease_present": (
            substrate.get("lease") is None
            or substrate.get("obligation_epoch_gap_ok") is True
        ),
        "baseline_rollup": snapshot.get("baseline_rollup"),
        "canonical_entrypoint": snapshot.get("canonical_entrypoint"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_c3_pass = all(checks.values())
    return {
        "step": P0_C3_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "snapshot_text": snapshot_text,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_c3_pass": p0_c3_pass,
        "verification": {
            "step_c3_pass": p0_c3_pass,
            "cleared_for_c4": p0_c3_pass,
            "unified_ops_entrypoint": checks.get("unified_command_emits_json_fields"),
        },
    }
