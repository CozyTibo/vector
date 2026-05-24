"""S5.4 — unified operational truth model (two scripts, two panels)."""

from __future__ import annotations

from typing import Any, Final

OPERATIONAL_TRUTH_SCHEMA_VERSION: Final[int] = 1
WAVE_S5_STEP_24: Final[str] = "wave_s5_operational_truth_model"

RULE_M3_AA_NOT_SEMANTIC_GREEN: Final[str] = "m3_aa_pass_ne_semantic_green"

RUNTIME_CONTINUITY_TRACK_V1: Final[dict[str, Any]] = {
    "track_id": "runtime_continuity",
    "script": "backend/scripts/continuity_audit_snapshot.py",
    "admin_panel": "continuity_overview",
    "authoritative_source": "convergence_lease_fsm",
    "primary_metrics": ["lease_fsm", "aa_panel", "phase_receipts"],
}

SEMANTIC_READINESS_TRACK_V1: Final[dict[str, Any]] = {
    "track_id": "semantic_readiness",
    "script": "backend/scripts/graph_truth_audit_snapshot.py",
    "admin_panel": "semantic_readiness",
    "authoritative_source": "graph_truth_and_retrieval_mix",
    "primary_metrics": ["unique_auth_pairs", "dup_factor", "retrieval_mix", "published_claims_7d"],
}


def build_runtime_track_attachment_v1() -> dict[str, Any]:
    return {
        "schema_version": OPERATIONAL_TRUTH_SCHEMA_VERSION,
        **RUNTIME_CONTINUITY_TRACK_V1,
        "companion_track": SEMANTIC_READINESS_TRACK_V1["track_id"],
        "policy": "lease_status_over_pipeline_completed",
    }


def build_semantic_track_attachment_v1() -> dict[str, Any]:
    return {
        "schema_version": OPERATIONAL_TRUTH_SCHEMA_VERSION,
        **SEMANTIC_READINESS_TRACK_V1,
        "companion_track": RUNTIME_CONTINUITY_TRACK_V1["track_id"],
        "policy": "unique_pairs_and_retrieval_mix_over_raw_link_counts",
    }


def summarize_runtime_track_v1(
    *,
    continuity_status: dict[str, Any] | None = None,
    audit_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status = dict(continuity_status or {})
    summary = dict(audit_summary or {})
    state = str(status.get("state") or "").upper()
    execution_lane = str(status.get("execution_lane") or "")
    m3_alive = bool(summary.get("m3_autonomously_alive"))
    panel_fail = int(summary.get("panel_fail_count") or 0)
    runtime_green = state == "AUTONOMOUS" and execution_lane == "HEALTHY" and panel_fail == 0
    if summary and m3_alive and panel_fail == 0 and state in ("AUTONOMOUS", "DEGRADED"):
        runtime_green = runtime_green or (m3_alive and panel_fail == 0 and execution_lane != "BLOCKED")
    return {
        "track_id": RUNTIME_CONTINUITY_TRACK_V1["track_id"],
        "runtime_green": runtime_green,
        "continuity_state": state or None,
        "execution_lane": execution_lane or None,
        "m3_autonomously_alive": m3_alive if summary else None,
        "panel_fail_count": panel_fail if summary else None,
    }


def summarize_semantic_track_v1(*, semantic_readiness: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(semantic_readiness or {})
    panel = list(payload.get("semantic_operator_panel") or [])
    bad_metrics = [m for m in panel if str(m.get("severity") or "") == "bad"]
    g = dict(payload.get("graph_truth") or {})
    dup_sev = str(g.get("dup_factor_severity") or "")
    semantic_green = bool(panel) and not bad_metrics and dup_sev in ("ok", "unknown")
    return {
        "track_id": SEMANTIC_READINESS_TRACK_V1["track_id"],
        "semantic_green": semantic_green,
        "bad_metric_keys": [str(m.get("key")) for m in bad_metrics],
        "dup_factor_severity": dup_sev or None,
        "unique_auth_pairs": g.get("unique_auth_pairs"),
    }


def build_operational_truth_cross_check_v1(
    *,
    continuity_status: dict[str, Any] | None = None,
    audit_summary: dict[str, Any] | None = None,
    semantic_readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime = summarize_runtime_track_v1(
        continuity_status=continuity_status,
        audit_summary=audit_summary,
    )
    semantic = summarize_semantic_track_v1(semantic_readiness=semantic_readiness)
    runtime_green = bool(runtime.get("runtime_green"))
    semantic_green = bool(semantic.get("semantic_green"))
    rule_active = runtime_green and not semantic_green
    message = (
        "Runtime AA/M3 PASS does not imply semantic green — check graph truth and retrieval mix."
        if rule_active
        else "Both tracks must pass for full operational sign-off."
    )
    return {
        "schema_version": OPERATIONAL_TRUTH_SCHEMA_VERSION,
        "step": WAVE_S5_STEP_24,
        "rule": RULE_M3_AA_NOT_SEMANTIC_GREEN,
        "rule_active": rule_active,
        "runtime_track": runtime,
        "semantic_track": semantic,
        "runtime_track_green": runtime_green,
        "semantic_track_green": semantic_green,
        "combined_operational_green": runtime_green and semantic_green,
        "operator_message": message,
        "tracks": [RUNTIME_CONTINUITY_TRACK_V1, SEMANTIC_READINESS_TRACK_V1],
    }
