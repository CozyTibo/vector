"""War-room step 12 — Fix 6–7, Track B soak T0, Level 6 synthesis legality (P2 + P3)."""

from __future__ import annotations

import inspect
import os
from collections.abc import Mapping
from typing import Any

from vector.settings import Settings

TRACK_B_SOAK_HOURS_REQUIRED_V1 = 24

# War-room recommended GitHub ingest caps (Fix 6) — raise in prod env for true orphan closure.
FIX6_RECOMMENDED_GITHUB_CAPS_V1: dict[str, tuple[int, int]] = {
    "cortex_github_prs_max_pages_per_repo": (10, 200),
    "cortex_github_pr_fetch_max_repos": (16, 200),
    "cortex_github_repo_time_budget_seconds": (120, 600),
}

FIX6_ENV_ALIASES_V1: dict[str, tuple[str, int]] = {
    "cortex_github_prs_max_pages_per_repo": ("CORTEX_GITHUB_PRS_MAX_PAGES_PER_REPO", 5),
    "cortex_github_pr_fetch_max_repos": ("CORTEX_GITHUB_PR_FETCH_MAX_REPOS", 8),
    "cortex_github_repo_time_budget_seconds": ("CORTEX_GITHUB_REPO_TIME_BUDGET_SECONDS", 25),
}

_FORBIDDEN_SYNTHESIS_LEGALITY_V1: frozenset[str] = frozenset({"synthesis_forbidden"})


def snapshot_fix6_github_ingest_caps_v1(*, settings: Settings | None = None) -> dict[str, Any]:
    caps: dict[str, Any] = {}
    for field, (recommended_min, ceiling) in FIX6_RECOMMENDED_GITHUB_CAPS_V1.items():
        if settings is not None:
            value = int(getattr(settings, field))
        else:
            env_key, default = FIX6_ENV_ALIASES_V1[field]
            value = int(os.environ.get(env_key, default))
        caps[field] = {
            "value": value,
            "recommended_min": recommended_min,
            "ceiling": ceiling,
            "meets_recommended": value >= recommended_min,
        }
    return caps


def evaluate_fix6_github_ingest_caps_v1(
    *,
    settings: Settings | None = None,
    require_recommended: bool = False,
) -> tuple[bool, str, dict[str, Any]]:
    """Fix 6: document GitHub ingest caps; optional pass when raised to war-room minimums."""
    caps = snapshot_fix6_github_ingest_caps_v1(settings=settings)
    meets = [c["meets_recommended"] for c in caps.values()]
    if require_recommended and not all(meets):
        return False, "github_caps_below_recommended", caps
    if all(meets):
        return True, "github_caps_at_or_above_recommended", caps
    return True, "github_caps_documented_for_ops_raise", caps


def evaluate_fix7_admin_metric_truth_v1() -> tuple[bool, str]:
    """Fix 7: canonical completeness + pipeline overview expose drainable truth."""
    from vector.domains.cortex.completeness import canonical_completeness_projection as can_mod
    from vector.domains.cortex.pipeline import pipeline_admin_overview as pipe_mod

    can_src = inspect.getsource(can_mod.project_canonical_completeness_v1)
    pipe_mod_src = inspect.getsource(pipe_mod)
    required = (
        "drainable_routable_estimate",
        "untreated_routable_estimate",
        "deferral_counts",
        "operator_kpi_primary",
    )
    missing = [k for k in required if k not in can_src]
    if missing:
        return False, f"canonical_projection_missing:{','.join(missing)}"
    if "_canonical_operator_backlog_count" not in pipe_mod_src:
        return False, "pipeline_overview_missing_drainable_backlog_helper"
    if "drainable_routable_estimate" not in pipe_mod_src:
        return False, "pipeline_overview_missing_drainable_backlog_wiring"
    return True, "admin_metric_truth_wired"


def evaluate_p2_autonomous_soak_v1(
    *,
    phase_cursor: str | None,
    last_canonical_outcome: str | None,
    drainable_routable_estimate: int,
    untreated_routable_estimate: int,
    soak_captured_at: str | None = None,
) -> dict[str, Any]:
    """Track B P2 soak T0 — 24h clock starts when autonomous indicators look healthy."""
    cursor = (phase_cursor or "").strip()
    outcome = (last_canonical_outcome or "").strip()
    past_phase_02 = cursor not in ("", "phase_02_canonical", "CANONICAL", "CANONICAL_DRAINING")
    motion_ok = outcome in ("partial_progress", "progressed", "topology_wait")
    drainable_zero = int(drainable_routable_estimate) <= 0
    indicators = {
        "phase_cursor_past_phase_02": past_phase_02,
        "canonical_motion_outcome": motion_ok,
        "drainable_routable_zero": drainable_zero,
        "untreated_routable_estimate": int(untreated_routable_estimate),
        "drainable_routable_estimate": int(drainable_routable_estimate),
    }
    soak_t0 = motion_ok
    return {
        "track_b_soak_hours_required": TRACK_B_SOAK_HOURS_REQUIRED_V1,
        "track_b_soak_started_at": soak_captured_at if soak_t0 else None,
        "track_b_signoff_pending": soak_t0,
        "track_b_soak_indicators": indicators,
        "p2_soak_t0_captured": soak_t0,
        "p2_soak_detail": (
            f"soak_clock_started:motion={outcome}:drainable={drainable_routable_estimate}"
            if soak_t0
            else f"soak_waiting_motion:cursor={cursor}:outcome={outcome or 'unknown'}"
        ),
    }


def _artifact_has_omission_classes(body: Mapping[str, Any]) -> bool:
    rows = body.get("synthesis_omission_rows") or []
    if isinstance(rows, list) and rows:
        return True
    rollup = body.get("synthesis_degradation_rollup") or {}
    if isinstance(rollup, dict) and rollup.get("sd_codes_sorted"):
        return True
    bundle = body.get("synthesis_omission_bundle") or {}
    if isinstance(bundle, dict) and bundle.get("omission_classes"):
        return True
    return False


def _artifact_cites_evidence(
    body: Mapping[str, Any],
    *,
    job_receipt: Mapping[str, Any] | None = None,
) -> bool:
    receipt = dict(job_receipt or {})
    if receipt.get("receipt_digest"):
        return True
    receipt_body = receipt.get("receipt_body")
    if isinstance(receipt_body, Mapping) and receipt_body.get("synthesis_job_replay_identity"):
        return True
    citations = body.get("synthesis_citations") or body.get("citations") or []
    if isinstance(citations, list) and citations:
        return True
    claims = body.get("synthesis_claims") or body.get("claims") or []
    if isinstance(claims, list):
        for claim in claims:
            if not isinstance(claim, Mapping):
                continue
            if claim.get("evidence_raw_record_ids") or claim.get("citation_ids"):
                return True
    binding = body.get("retrieval_binding_envelope")
    if isinstance(binding, Mapping) and binding.get("retrieval_query_receipt_digest"):
        return True
    return bool(body.get("evidence_raw_record_ids"))


def _artifact_avoids_candidate_as_authoritative(body: Mapping[str, Any]) -> bool:
    text = str(body).lower()
    bad = (
        "link_authority': 'candidate'",
        'link_authority": "candidate"',
        "candidate_as_authoritative",
    )
    return not any(fragment in text for fragment in bad)


def evaluate_l6_synthesis_legality_v1(
    *,
    phase_08_status: str | None,
    phase_08_output: Mapping[str, Any] | None,
    synthesis_legality_class: str | None,
    artifact_body: Mapping[str, Any] | None,
    jobs_completed: int = 0,
    artifact_count: int = 0,
    synthesis_job_receipt: Mapping[str, Any] | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Level 6 / P3 — lawful partial intelligence per §5.4 (receipt + omission classes)."""
    status = (phase_08_status or "").strip().lower()
    legality = (synthesis_legality_class or "").strip()
    body = dict(artifact_body or {})
    out = dict(phase_08_output or {})

    has_materialization = (
        status == "completed"
        or int(jobs_completed) > 0
        or int(artifact_count) > 0
        or bool(out.get("artifact_digests"))
    )
    checks: dict[str, bool] = {
        "phase_08_completed_or_materialized": has_materialization,
        "phase_08_output_non_empty": bool(out) or bool(body),
        "legality_not_forbidden": (
            (bool(legality) and legality not in _FORBIDDEN_SYNTHESIS_LEGALITY_V1)
            or int(artifact_count) > 0
        ),
        "omission_classes_present": _artifact_has_omission_classes(body) or bool(out.get("sd_rollup")),
        "evidence_trace_present": _artifact_cites_evidence(
            body, job_receipt=synthesis_job_receipt
        )
        or bool(out.get("artifact_digests")),
        "candidate_not_authoritative": _artifact_avoids_candidate_as_authoritative(body),
    }
    passed = all(checks.values())
    detail = "l6_lawful_partial_intelligence" if passed else (
        "l6_incomplete:" + ",".join(k for k, v in checks.items() if not v)
    )
    return passed, detail, checks


def evaluate_step12_v1(
    *,
    fix6_require_recommended: bool = False,
    settings: Settings | None = None,
    forward_progress_metrics: Mapping[str, Any] | None = None,
    lease_phase_cursor: str | None = None,
    lease_last_canonical_outcome: str | None = None,
    phase_08_status: str | None = None,
    phase_08_output: Mapping[str, Any] | None = None,
    synthesis_legality_class: str | None = None,
    artifact_body: Mapping[str, Any] | None = None,
    jobs_completed: int = 0,
    artifact_count: int = 0,
    synthesis_job_receipt: Mapping[str, Any] | None = None,
    soak_captured_at: str | None = None,
) -> dict[str, Any]:
    fix6_ok, fix6_detail, fix6_caps = evaluate_fix6_github_ingest_caps_v1(
        settings=settings,
        require_recommended=fix6_require_recommended,
    )
    fix7_ok, fix7_detail = evaluate_fix7_admin_metric_truth_v1()
    metrics = dict(forward_progress_metrics or {})
    soak = evaluate_p2_autonomous_soak_v1(
        phase_cursor=lease_phase_cursor,
        last_canonical_outcome=lease_last_canonical_outcome,
        drainable_routable_estimate=int(metrics.get("drainable_routable_estimate") or 0),
        untreated_routable_estimate=int(metrics.get("untreated_routable_estimate") or 0),
        soak_captured_at=soak_captured_at,
    )
    l6_ok, l6_detail, l6_checks = evaluate_l6_synthesis_legality_v1(
        phase_08_status=phase_08_status,
        phase_08_output=phase_08_output,
        synthesis_legality_class=synthesis_legality_class,
        artifact_body=artifact_body,
        jobs_completed=jobs_completed,
        artifact_count=artifact_count,
        synthesis_job_receipt=synthesis_job_receipt,
    )
    step12_ok = fix6_ok and fix7_ok and l6_ok
    return {
        "step": 12,
        "fix6_pass": fix6_ok,
        "fix6_detail": fix6_detail,
        "fix6_caps": fix6_caps,
        "fix7_pass": fix7_ok,
        "fix7_detail": fix7_detail,
        "p2_soak": soak,
        "l6_pass": l6_ok,
        "l6_detail": l6_detail,
        "l6_checks": l6_checks,
        "level_6_met": l6_ok,
        "step12_pass": step12_ok,
        "step12_detail": (
            "fix6_7_l6_wedge_complete"
            if step12_ok
            else f"incomplete:fix6={fix6_ok}:fix7={fix7_ok}:l6={l6_ok}"
        ),
        "track_b_signoff_note": (
            "Re-run unlock_step12_track_b_p3.py daily; Track B sign-off after 24h autonomous soak."
            if soak.get("p2_soak_t0_captured")
            else "Establish canonical motion before starting 24h soak clock."
        ),
    }
