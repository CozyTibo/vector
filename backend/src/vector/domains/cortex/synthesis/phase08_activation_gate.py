"""Phase 08 activation gating for the execution slice (not CESP CI gates)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_eligible_scopes_v1,
)
from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
    explain_synthesis_eligibility_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

SYNTHESIS_ACTIVATION_TRIGGER_AFTER_PHASE_07_V1: Final[str] = "after_phase_07"
SYNTHESIS_ACTIVATION_TRIGGER_MANUAL_V1: Final[str] = "manual"


def get_synthesis_forbidden_backoff_threshold_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_synthesis_forbidden_backoff_threshold))
    except Exception:  # noqa: BLE001
        return 3


def get_synthesis_forbidden_backoff_window_hours_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_synthesis_forbidden_backoff_window_hours))
    except Exception:  # noqa: BLE001
        return 24


def is_phase_08_pipeline_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_substrate_pipeline_phase_08_enabled)
    except Exception:  # noqa: BLE001
        return True


def count_recent_synthesis_forbidden_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    window_hours = get_synthesis_forbidden_backoff_window_hours_v1()
    since = datetime.now(tz=UTC) - timedelta(hours=window_hours)
    forbidden_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.synthesis_legality_class == "synthesis_forbidden",
                CortexSynthesisJob.created_at >= since,
            )
        )
        or 0
    )
    threshold = get_synthesis_forbidden_backoff_threshold_v1()
    return {
        "forbidden_count": forbidden_count,
        "forbidden_backoff_threshold": threshold,
        "forbidden_backoff_window_hours": window_hours,
        "forbidden_backoff_active": forbidden_count >= threshold,
    }


def compute_min_synthesis_jobs_target_v1(
    *,
    eligible_scopes: int,
    max_scopes: int,
) -> int:
    if eligible_scopes <= 0:
        return 0
    return min(int(eligible_scopes), max(1, int(max_scopes)))


def evaluate_synthesis_activation_schedule_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    published_index_epoch: str | None = None,
    trigger: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Whether phase 08 synthesis activation should run for this tenant/pipeline."""
    scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
    eligible = int(scope.get("eligible_scopes") or 0)
    index_epoch = published_index_epoch or scope.get("published_index_epoch")
    from vector.domains.cortex.synthesis.synthesis_pipeline import synthesis_pipeline_max_scopes_v1

    max_scopes = synthesis_pipeline_max_scopes_v1()
    min_jobs_target = compute_min_synthesis_jobs_target_v1(
        eligible_scopes=eligible,
        max_scopes=max_scopes,
    )
    forbidden_metrics = count_recent_synthesis_forbidden_v1(session, tenant_id=tenant_id)
    phase_08_enabled = is_phase_08_pipeline_enabled_v1()
    eligibility = explain_synthesis_eligibility_v1(session, tenant_id=tenant_id)

    should = False
    reason = "unknown"
    must_run_phase_08 = eligible > 0 and phase_08_enabled

    if not phase_08_enabled:
        reason = "phase_08_disabled"
    elif forbidden_metrics["forbidden_backoff_active"] and not force:
        reason = "synthesis_forbidden_backoff"
    elif must_run_phase_08:
        should = True
        reason = "eligible_scopes_require_phase_08"
    elif phase_08_enabled:
        should = True
        reason = "phase_08_enabled_optional_empty_eligible"

    return {
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else None,
        "trigger": trigger,
        "should_activate": should,
        "must_run_phase_08": must_run_phase_08,
        "activation_reason": reason,
        "phase_08_enabled": phase_08_enabled,
        "eligible_scopes": eligible,
        "published_index_epoch": index_epoch,
        "max_scopes_per_pass": max_scopes,
        "min_jobs_target": min_jobs_target,
        "forbidden_backoff": forbidden_metrics,
        "eligibility_summary": {
            "synthesis_ready": eligibility.get("synthesis_ready"),
            "blocked_by": list(eligibility.get("blocked_by") or []),
            "next_required_step": eligibility.get("next_required_step"),
        },
    }
