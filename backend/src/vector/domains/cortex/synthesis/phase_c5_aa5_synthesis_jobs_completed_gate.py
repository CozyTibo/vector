"""Phase C step C5 — AA5 requires synthesis jobs_completed > 0 (not merely started)."""

from __future__ import annotations

from typing import Any, Final

PHASE_C5_AA5_GATE_SCHEMA_VERSION: Final[int] = 1
P0_C5_STEP: Final[str] = "step_c5_aa5_synthesis_jobs_completed"
AA5_JOBS_COMPLETED_CODE_V1: Final[str] = "aa5_requires_jobs_completed"
AA5_LEGACY_STARTED_ONLY_CODE_V1: Final[str] = "aa5_legacy_started_only_advisory"


def is_aa5_require_jobs_completed_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_aa5_require_jobs_completed)
    except Exception:  # noqa: BLE001
        return True


def evaluate_aa5_synthesis_jobs_completed_gate_v1(
    phase08: dict[str, Any],
    *,
    phase_08_started_at: str | None = None,
    phase_08_status: str | None = None,
    pipeline_run_id: str | None = None,
) -> dict[str, Any]:
    """Evaluate AA5 truth: jobs_completed > 0 or lawful empty (C5 / S2 / S3)."""
    from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
        _lawful_empty_synthesis_v1,
    )

    jobs_completed = int(phase08.get("jobs_completed") or 0)
    useful_published = int(phase08.get("useful_artifacts_published") or 0)
    scopes_scheduled = int(phase08.get("scopes_scheduled") or 0)
    lawful_empty = _lawful_empty_synthesis_v1(phase08)
    started = phase_08_started_at is not None
    strict = is_aa5_require_jobs_completed_enabled_v1()

    if jobs_completed > 0 and useful_published >= 1:
        verdict = "PASS"
        detail = "synthesis_jobs_completed_with_useful_artifact"
    elif jobs_completed > 0:
        verdict = "FAIL"
        detail = "synthesis_jobs_completed_without_useful_artifact"
    elif lawful_empty:
        verdict = "PASS"
        detail = "lawful_empty_synthesis"
    elif not started:
        verdict = "FAIL"
        detail = "phase_08_never_started"
    elif strict:
        verdict = "FAIL"
        detail = "phase_08_started_without_jobs_completed"
    else:
        verdict = "ADVISORY"
        detail = "legacy_started_only_aa5_advisory"

    return {
        "gate_id": "AA5",
        "verdict": verdict,
        "pass": verdict == "PASS",
        "criterion": (
            "phase_08 jobs_completed > 0 with useful artifact (S4.3) or lawful documented empty (C5)"
            if strict
            else "phase_08.started_at IS NOT NULL (legacy advisory)"
        ),
        "detail": detail,
        "evidence": {
            "pipeline_run_id": pipeline_run_id,
            "phase_08_status": phase_08_status,
            "phase_08_started_at": phase_08_started_at,
            "jobs_completed": jobs_completed,
            "jobs_failed": int(phase08.get("jobs_failed") or 0),
            "scopes_scheduled": scopes_scheduled,
            "scope_empty": bool(phase08.get("scope_empty")),
            "lawful_empty": lawful_empty,
            "artifacts_published": int(phase08.get("artifacts_published") or 0),
            "useful_artifacts_published": useful_published,
            "aa5_strict_jobs_completed_required": strict,
            "phase_c5_schema_version": PHASE_C5_AA5_GATE_SCHEMA_VERSION,
            "fake_started_only_would_pass_legacy": started and jobs_completed == 0 and not lawful_empty,
        },
        "error_code": (
            AA5_JOBS_COMPLETED_CODE_V1
            if verdict == "FAIL"
            and detail
            in (
                "phase_08_started_without_jobs_completed",
                "synthesis_jobs_completed_without_useful_artifact",
            )
            else None
        ),
    }
