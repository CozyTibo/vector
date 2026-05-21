"""Phase 08.5 P085-24 — synthesis activation scheduler (**G-P085-SYN-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-synthesis-activation-doctrine.md`` §Continuous activation.
"""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final, Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_eligible_scopes_v1,
)
from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
    explain_synthesis_eligibility_v1,
)
from vector.domains.cortex.synthesis.synthesis_pipeline import (
    materialize_synthesis_for_pipeline_v1,
    synthesis_pipeline_max_scopes_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

PHASE085_SYNTHESIS_ACTIVATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_SYNTHESIS_ACTIVATION_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-synthesis-activation-doctrine.md"
)

GP085_SYN01_GATE_ID_V1: Final[str] = "G-P085-SYN-01"

CELERY_SYNTHESIS_ACTIVATION_SCHEDULE_TASK_NAME_V1: Final[str] = (
    "vector.cortex.operational_runtime.schedule_synthesis_activation_for_tenant"
)

SYNTHESIS_ACTIVATION_TRIGGER_AFTER_PHASE_07_V1: Final[str] = "after_phase_07"
SYNTHESIS_ACTIVATION_TRIGGER_MANUAL_V1: Final[str] = "manual"


class SubstrateSynthesisActivationSchedulingError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


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
    """Count recent ``synthesis_forbidden`` jobs for backoff (**G-P085-SYN-01**)."""
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
    """Minimum jobs per activation pass: ``min(eligible, max_scopes)`` unless legality blocks."""
    if eligible_scopes <= 0:
        return 0
    return min(int(eligible_scopes), max(1, int(max_scopes)))


def build_synthesis_forbidden_escalation_panel_v1(
    *,
    tenant_id: uuid.UUID,
    forbidden_metrics: Mapping[str, Any],
    eligibility: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Operator panel when repeated ``synthesis_forbidden`` blocks automatic activation."""
    count = int(forbidden_metrics.get("forbidden_count") or 0)
    threshold = int(forbidden_metrics.get("forbidden_backoff_threshold") or 3)
    window = int(forbidden_metrics.get("forbidden_backoff_window_hours") or 24)
    messages = [
        (
            f"Synthesis activation paused: {count} synthesis_forbidden job(s) in the last "
            f"{window}h (threshold {threshold})."
        ),
        "Resolve legality upstream (retrieval pins, policy pack, replay posture) before retrying.",
        "Use admin synthesis legality APIs or POST .../synthesis-activation-scheduling/run with force=true.",
    ]
    return {
        "panel_title": "Synthesis forbidden backoff",
        "messages": messages,
        "forbidden_metrics": dict(forbidden_metrics),
        "eligibility": dict(eligibility or {}),
        "tenant_id": str(tenant_id),
    }


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
        "gate_id": GP085_SYN01_GATE_ID_V1,
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


def chain_synthesis_activation_after_phase07_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    published_index_epoch: str | None = None,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Chain phase 08 after phase 07 publish with **G-P085-SYN-01** activation law."""
    eval_out = evaluate_synthesis_activation_schedule_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        published_index_epoch=published_index_epoch,
        trigger=SYNTHESIS_ACTIVATION_TRIGGER_AFTER_PHASE_07_V1,
        force=force,
    )

    if not eval_out["phase_08_enabled"]:
        from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
            mark_continuation_completed_v1,
        )
        from vector.domains.cortex.substrate_pipeline.repository import skip_phase_v1

        skip_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_08_SYNTHESIS,
            reason="phase_08_disabled",
        )
        from vector.domains.cortex.substrate_pipeline.orchestrator import (
            finalize_pipeline_if_complete_v1,
        )

        fin = finalize_pipeline_if_complete_v1(session, pipeline_run_id=pipeline_run_id)
        return {
            "chained": False,
            "phase_08_skipped": True,
            "finalize": fin,
            "activation_evaluation": eval_out,
        }

    if not eval_out["should_activate"]:
        panel = build_synthesis_forbidden_escalation_panel_v1(
            tenant_id=tenant_id,
            forbidden_metrics=dict(eval_out["forbidden_backoff"]),
            eligibility=eval_out.get("eligibility_summary"),
        )
        return {
            "chained": False,
            "synthesis_forbidden_backoff": True,
            "activation_evaluation": eval_out,
            "synthesis_forbidden_escalation_panel": panel,
        }

    from vector.domains.cortex.substrate_pipeline.orchestrator import (
        enqueue_next_pipeline_phase_v1,
    )

    chain = enqueue_next_pipeline_phase_v1(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_08_SYNTHESIS,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
    )
    return {
        "chained": True,
        "activation_evaluation": eval_out,
        "next_phase_chain": chain,
        "min_jobs_target": eval_out["min_jobs_target"],
    }


def run_synthesis_activation_schedule_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    published_index_epoch: str | None = None,
    trigger: str = SYNTHESIS_ACTIVATION_TRIGGER_MANUAL_V1,
    force: bool = False,
    execute_inline: bool = True,
) -> dict[str, Any]:
    """Run synthesis activation inline or enqueue phase 08 Celery task."""
    prid = pipeline_run_id
    if prid is None:
        running = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
        if running is not None:
            prid = running.id

    eval_out = evaluate_synthesis_activation_schedule_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        published_index_epoch=published_index_epoch,
        trigger=trigger,
        force=force,
    )

    if not eval_out["should_activate"]:
        panel = None
        if eval_out["activation_reason"] == "synthesis_forbidden_backoff":
            panel = build_synthesis_forbidden_escalation_panel_v1(
                tenant_id=tenant_id,
                forbidden_metrics=dict(eval_out["forbidden_backoff"]),
            )
        return {
            "gate_id": GP085_SYN01_GATE_ID_V1,
            "activated": False,
            "reason": eval_out["activation_reason"],
            "evaluation": eval_out,
            "synthesis_forbidden_escalation_panel": panel,
        }

    if prid is None:
        return {
            "gate_id": GP085_SYN01_GATE_ID_V1,
            "activated": False,
            "reason": "no_pipeline_run_id",
            "evaluation": eval_out,
        }

    if execute_inline:
        from vector.domains.cortex.synthesis.synthesis_pipeline import (
            run_substrate_phase_08_synthesis_v1,
        )

        phase_out = run_substrate_phase_08_synthesis_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
        )
        return {
            "gate_id": GP085_SYN01_GATE_ID_V1,
            "activated": True,
            "execution_mode": "inline_phase_08",
            "evaluation": eval_out,
            "phase_08_output": phase_out,
        }

    from vector.domains.cortex.substrate_pipeline.orchestrator import (
        enqueue_next_pipeline_phase_v1,
    )

    chain = enqueue_next_pipeline_phase_v1(
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        phase_id=PHASE_08_SYNTHESIS,
    )
    return {
        "gate_id": GP085_SYN01_GATE_ID_V1,
        "activated": True,
        "execution_mode": "celery_phase_08",
        "evaluation": eval_out,
        "next_phase_chain": chain,
    }


def run_synthesis_activation_after_phase07_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    published_index_epoch: str | None = None,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
) -> dict[str, Any]:
    """Phase 07 completion hook — evaluate + chain phase 08 (**G-P085-SYN-01**)."""
    return chain_synthesis_activation_after_phase07_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        published_index_epoch=published_index_epoch,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
    )


def schedule_synthesis_activation_for_tenant_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    published_index_epoch: str | None = None,
    trigger: str = SYNTHESIS_ACTIVATION_TRIGGER_MANUAL_V1,
    countdown: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Enqueue async synthesis activation schedule pass."""
    from vector.infrastructure.db.session import session_scope

    with session_scope() as session:
        eval_out = evaluate_synthesis_activation_schedule_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            published_index_epoch=published_index_epoch,
            trigger=trigger,
            force=force,
        )
    if not force and not eval_out.get("should_activate"):
        return {
            "scheduled": False,
            "reason": eval_out.get("activation_reason"),
            "evaluation": eval_out,
        }

    _ = countdown
    with session_scope() as session:
        pass_out = run_synthesis_activation_schedule_pass_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            published_index_epoch=published_index_epoch,
            trigger=trigger,
            force=force,
        )
        session.commit()
    return {
        "scheduled": True,
        "path": "inline_execution_slice",
        "evaluation": eval_out,
        "pass": pass_out,
    }


def build_substrate_synthesis_activation_scheduling_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_synthesis_activation_runtime_schema_version": int(
            PHASE085_SYNTHESIS_ACTIVATION_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_SYNTHESIS_ACTIVATION_SPEC_REF_V1,
        "primary_gate_id": GP085_SYN01_GATE_ID_V1,
        "phase_08_setting": "CORTEX_SUBSTRATE_PIPELINE_PHASE_08_ENABLED",
        "max_scopes_setting": "CORTEX_SYNTHESIS_PIPELINE_MAX_SCOPES",
        "forbidden_backoff_threshold": get_synthesis_forbidden_backoff_threshold_v1(),
        "forbidden_backoff_window_hours": get_synthesis_forbidden_backoff_window_hours_v1(),
        "min_jobs_formula": "min(eligible_scopes, max_scopes_per_pass)",
        "activation_audit_table": "cortex_synthesis_activation_audits",
        "materialize_entrypoint": "materialize_synthesis_for_pipeline_v1",
        "celery_task_name": CELERY_SYNTHESIS_ACTIVATION_SCHEDULE_TASK_NAME_V1,
        "scheduler_entrypoint": "schedule_synthesis_activation_for_tenant_v1",
        "pass_entrypoint": "run_synthesis_activation_schedule_pass_v1",
        "phase07_hook": "run_synthesis_activation_after_phase07_v1",
        "schedule_triggers": [
            SYNTHESIS_ACTIVATION_TRIGGER_AFTER_PHASE_07_V1,
            SYNTHESIS_ACTIVATION_TRIGGER_MANUAL_V1,
        ],
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_synthesis_activation_scheduling"
        ),
    }


def verify_gp085_syn01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_synthesis_activation_scheduling_catalog_v1()
    if cat["primary_gate_id"] != GP085_SYN01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    if compute_min_synthesis_jobs_target_v1(eligible_scopes=10, max_scopes=4) != 4:
        errors.append("min_jobs_target_formula")
    if compute_min_synthesis_jobs_target_v1(eligible_scopes=2, max_scopes=32) != 2:
        errors.append("min_jobs_target_eligible_smaller")

    mat_src = inspect.getsource(materialize_synthesis_for_pipeline_v1)
    if "persist_synthesis_activation_audit_v1" not in mat_src:
        errors.append("materialize_missing_activation_audit")

    pass_src = inspect.getsource(run_synthesis_activation_schedule_pass_v1)
    if "random" in pass_src.lower():
        errors.append("probabilistic_activation_forbidden")

    from vector.domains.cortex.substrate_pipeline import orchestrator as orch_mod

    pub_src = inspect.getsource(orch_mod.on_retrieval_publish_completed_for_pipeline_v1)
    if "chain_synthesis_activation_after_phase07_v1" not in pub_src:
        errors.append("orchestrator_missing_activation_chain")

    from vector.domains.cortex.substrate_pipeline import phase_runners as pr

    p07_src = inspect.getsource(pr.run_phase_07_retrieval_v1)
    if "run_synthesis_activation_after_phase07_v1" not in p07_src:
        errors.append("phase07_missing_activation_hook")

    eval_src = inspect.getsource(evaluate_synthesis_activation_schedule_v1)
    if "synthesis_forbidden_backoff" not in eval_src:
        errors.append("evaluate_missing_forbidden_backoff")

    import importlib.util

    if importlib.util.find_spec("app.tasks.cortex_substrate_synthesis_activation_scheduling") is not None:
        errors.append("celery_synthesis_activation_module_must_be_deleted_m9")

    passed = not errors
    return {
        "id": GP085_SYN01_GATE_ID_V1,
        "name": "cesp_substrate_synthesis_activation_scheduling",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
