"""Phase 08.5 P085-18 — TCRE saturation scheduler (**G-P085-TCRE-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-tcre-maturity-doctrine.md`` §Saturation scheduler.
"""

from __future__ import annotations

import inspect
import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_density import (
    METRIC_TCRE_DENSITY_SCORE_V1,
    METRIC_TCRE_SATURATION_PERCENT_V1,
    compute_tcre_density_metrics_v1,
)
from vector.domains.cortex.reasoning.runtime.runtime_scope import (
    TCRE_RUNTIME_SLICE_DEFAULT_LIMIT,
)
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    enqueue_reconstruction_job_v1,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

PHASE085_TCRE_SATURATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_TCRE_SATURATION_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-tcre-maturity-doctrine.md"
)

GP085_TCRE01_GATE_ID_V1: Final[str] = "G-P085-TCRE-01"

CELERY_TCRE_SATURATION_SCHEDULE_TASK_NAME_V1: Final[str] = (
    "vector.cortex.operational_runtime.schedule_tcre_saturation_for_tenant"
)

TCRE_SATURATION_TRIGGER_AFTER_PHASE_06_V1: Final[str] = "after_phase_06"
TCRE_SATURATION_TRIGGER_WATCHDOG_V1: Final[str] = "continuity_watchdog"
TCRE_SATURATION_TRIGGER_MANUAL_V1: Final[str] = "manual"

class SubstrateTcreSaturationSchedulingError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_tcre_saturation_threshold_v1() -> float:
    try:
        from vector.settings import get_settings

        return max(0.0, min(1.0, float(get_settings().cortex_tcre_saturation_threshold)))
    except Exception:  # noqa: BLE001
        return 0.85


def get_tcre_saturation_jobs_per_hour_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_tcre_saturation_jobs_per_hour))
    except Exception:  # noqa: BLE001
        return 4


def get_tcre_saturation_max_queued_jobs_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_tcre_saturation_max_queued_jobs))
    except Exception:  # noqa: BLE001
        return 8


def get_tcre_saturation_pass_max_jobs_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_tcre_saturation_pass_max_jobs))
    except Exception:  # noqa: BLE001
        return 4


def compute_tcre_saturation_metrics_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Saturation scheduler view — delegates density metrics (**G-P085-TCRE-02**)."""
    density = compute_tcre_density_metrics_v1(session, tenant_id=tenant_id)
    dm = dict(density["metrics"])

    queued_running = int(
        session.scalar(
            select(func.count())
            .select_from(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status.in_(("queued", "running")),
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
        )
        or 0
    )

    hour_ago = datetime.now(tz=UTC) - timedelta(hours=1)
    jobs_last_hour = int(
        session.scalar(
            select(func.count())
            .select_from(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.job_kind == "reconstruct",
                CortexTcreReconstructionJob.created_at >= hour_ago,
            )
        )
        or 0
    )

    mat_total = int(dm["tcre_materialization_total"])
    reconstructed = int(dm["tcre_reconstructed_count"])
    saturation_ratio = float(dm.get("saturation_ratio") or 0.0)

    return {
        "tenant_id": str(tenant_id),
        METRIC_TCRE_SATURATION_PERCENT_V1: dm[METRIC_TCRE_SATURATION_PERCENT_V1],
        METRIC_TCRE_DENSITY_SCORE_V1: dm[METRIC_TCRE_DENSITY_SCORE_V1],
        "tcre_materialization_total": mat_total,
        "tcre_reconstructed_count": reconstructed,
        "tcre_pending_count": int(dm["tcre_pending_count"]),
        "saturation_ratio": saturation_ratio,
        "saturation_threshold": get_tcre_saturation_threshold_v1(),
        "tcre_maturity_class": density["tcre_maturity_class"],
        "queued_running_jobs": queued_running,
        "jobs_enqueued_last_hour": jobs_last_hour,
        "reconstruction_not_yet_run": bool(dm.get("reconstruction_never_run")),
        "substrate_state": density["substrate_state"],
    }


def _estimate_jobs_to_reach_saturation_v1(
    *,
    mat_total: int,
    reconstructed: int,
    threshold: float,
) -> int:
    if mat_total <= 0:
        return 0
    target = int(math.ceil(float(mat_total) * float(threshold)))
    gap = max(0, target - int(reconstructed))
    if gap <= 0:
        return 0
    per_job = max(1, int(TCRE_RUNTIME_SLICE_DEFAULT_LIMIT))
    return max(1, int(math.ceil(float(gap) / float(per_job))))


def evaluate_tcre_saturation_schedule_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    trigger: str | None = None,
) -> dict[str, Any]:
    """Whether to enqueue additional TCRE reconstruction jobs."""
    metrics = compute_tcre_saturation_metrics_v1(session, tenant_id=tenant_id)
    mat_total = int(metrics["tcre_materialization_total"])
    saturation_ratio = float(metrics["saturation_ratio"])
    threshold = float(metrics["saturation_threshold"])
    queued = int(metrics["queued_running_jobs"])
    jobs_hour = int(metrics["jobs_enqueued_last_hour"])
    jobs_per_hour = get_tcre_saturation_jobs_per_hour_v1()
    max_queued = get_tcre_saturation_max_queued_jobs_v1()

    from vector.domains.cortex.operational_runtime.substrate_replay_storm_handling import (
        is_saturation_blocked_by_replay_storm_v1,
    )

    should = False
    reason = "unknown"
    upstream_cap_omission: dict[str, Any] | None = None
    if mat_total <= 0:
        reason = "no_canonical_materializations"
    elif saturation_ratio >= threshold:
        reason = "saturation_threshold_met"
    elif queued >= max_queued:
        reason = "tcre_queue_saturated"
    elif jobs_hour >= jobs_per_hour:
        reason = "hourly_job_budget_exhausted"
        from vector.domains.cortex.operational_runtime.substrate_runtime_economics import (
            build_upstream_cap_omission_v1,
        )

        upstream_cap_omission = build_upstream_cap_omission_v1(
            cap_kind="tcre_jobs_per_hour",
            detail=f"jobs_enqueued_last_hour={jobs_hour} cap={jobs_per_hour}",
            deferred_count=max(0, jobs_hour - jobs_per_hour + 1),
        )
    elif is_saturation_blocked_by_replay_storm_v1(session, tenant_id=tenant_id):
        reason = "replay_storm_operator_ack_required"
        from vector.domains.cortex.operational_runtime.substrate_replay_storm_handling import (
            OPERATIONAL_OMISSION_REPLAY_STORM_V1,
        )

        upstream_cap_omission = {
            "omission_class": OPERATIONAL_OMISSION_REPLAY_STORM_V1,
            "detail": reason,
        }
    else:
        should = True
        reason = "below_saturation_threshold"

    return {
        "gate_id": GP085_TCRE01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "trigger": trigger,
        "should_schedule": should,
        "schedule_reason": reason,
        "estimated_jobs_to_threshold": _estimate_jobs_to_reach_saturation_v1(
            mat_total=mat_total,
            reconstructed=int(metrics["tcre_reconstructed_count"]),
            threshold=threshold,
        ),
        "jobs_remaining_hourly_budget": max(0, jobs_per_hour - jobs_hour),
        "upstream_cap_omission": upstream_cap_omission,
        **metrics,
    }


def _build_saturation_job_scope_v1(
    *,
    pipeline_run_id: uuid.UUID | None,
    octs_walk_id: str | None,
) -> dict[str, Any]:
    scope: dict[str, Any] = {
        "octs_strict_binding": False,
        "materialization_limit": TCRE_RUNTIME_SLICE_DEFAULT_LIMIT,
    }
    if pipeline_run_id is not None:
        scope["substrate_pipeline_run_id"] = str(pipeline_run_id)
    if octs_walk_id:
        scope["octs_walk_id"] = str(octs_walk_id)
    return scope


def run_tcre_saturation_schedule_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    octs_walk_id: str | None = None,
    trigger: str = TCRE_SATURATION_TRIGGER_MANUAL_V1,
    skip_if_saturated: bool = True,
) -> dict[str, Any]:
    """Enqueue bounded TCRE jobs until saturation threshold (**G-P085-TCRE-01**)."""
    from vector.domains.cortex.operational_runtime.substrate_tcre_omission_explainability import (
        build_tcre_omission_explainability_panel_v1,
    )

    eval_out = evaluate_tcre_saturation_schedule_v1(
        session,
        tenant_id=tenant_id,
        trigger=trigger,
    )
    omission_panel = build_tcre_omission_explainability_panel_v1(session, tenant_id=tenant_id)
    if skip_if_saturated and not eval_out.get("should_schedule"):
        return {
            "gate_id": GP085_TCRE01_GATE_ID_V1,
            "tenant_id": str(tenant_id),
            "scheduled": False,
            "evaluation": eval_out,
            "enqueued_jobs": [],
            "tcre_omission_explainability_panel": omission_panel,
        }

    hourly_budget = int(eval_out.get("jobs_remaining_hourly_budget") or 0)
    pass_cap = get_tcre_saturation_pass_max_jobs_v1()
    estimate = int(eval_out.get("estimated_jobs_to_threshold") or 0)
    to_enqueue = max(0, min(pass_cap, hourly_budget, estimate))

    enqueued: list[dict[str, Any]] = []
    for _ in range(to_enqueue):
        re_eval = evaluate_tcre_saturation_schedule_v1(
            session,
            tenant_id=tenant_id,
            trigger=trigger,
        )
        if not re_eval.get("should_schedule"):
            break
        out = enqueue_reconstruction_job_v1(
            session,
            tenant_id=tenant_id,
            scope=_build_saturation_job_scope_v1(
                pipeline_run_id=pipeline_run_id,
                octs_walk_id=octs_walk_id,
            ),
            dry_run=False,
            run_sync=False,
        )
        enqueued.append(out)

    return {
        "gate_id": GP085_TCRE01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else None,
        "trigger": trigger,
        "scheduled": bool(enqueued),
        "jobs_enqueued": len(enqueued),
        "enqueued_jobs": enqueued,
        "evaluation": eval_out,
        "saturation_threshold": get_tcre_saturation_threshold_v1(),
        "jobs_per_hour_cap": get_tcre_saturation_jobs_per_hour_v1(),
        "tcre_omission_explainability_panel": omission_panel,
    }


def schedule_tcre_saturation_for_tenant_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    octs_walk_id: str | None = None,
    trigger: str = TCRE_SATURATION_TRIGGER_MANUAL_V1,
    countdown: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Enqueue async TCRE saturation schedule pass."""
    from vector.infrastructure.db.session import session_scope

    with session_scope() as session:
        eval_out = evaluate_tcre_saturation_schedule_v1(
            session,
            tenant_id=tenant_id,
            trigger=trigger,
        )
    if not force and not eval_out.get("should_schedule"):
        return {
            "scheduled": False,
            "reason": eval_out.get("schedule_reason"),
            "evaluation": eval_out,
        }

    cd = 0 if countdown is None else max(0, int(countdown))
    from app.tasks.cortex_substrate_tcre_saturation_scheduling import (
        run_tcre_saturation_schedule_pass_task,
    )

    async_result = run_tcre_saturation_schedule_pass_task.apply_async(
        kwargs={
            "tenant_id": str(tenant_id),
            "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else None,
            "octs_walk_id": octs_walk_id,
            "trigger": trigger,
            "force": force,
        },
        queue="vector",
        countdown=cd,
    )
    return {
        "scheduled": True,
        "celery_task_id": async_result.id,
        "task_name": CELERY_TCRE_SATURATION_SCHEDULE_TASK_NAME_V1,
        "countdown_seconds": cd,
        "evaluation": eval_out,
    }


def run_tcre_saturation_after_phase06_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    octs_walk_id: str | None = None,
    phase06_initial_job_enqueued: bool = True,
) -> dict[str, Any]:
    """Follow-up saturation pass after phase 06 enqueues the first TCRE job."""
    if phase06_initial_job_enqueued:
        metrics = compute_tcre_saturation_metrics_v1(session, tenant_id=tenant_id)
        if int(metrics["jobs_enqueued_last_hour"]) >= get_tcre_saturation_jobs_per_hour_v1():
            return {
                "gate_id": GP085_TCRE01_GATE_ID_V1,
                "scheduled": False,
                "reason": "hourly_budget_consumed_by_phase06_job",
            }
    return run_tcre_saturation_schedule_pass_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        octs_walk_id=octs_walk_id,
        trigger=TCRE_SATURATION_TRIGGER_AFTER_PHASE_06_V1,
        skip_if_saturated=True,
    )


def run_tcre_saturation_watchdog_hook_v1(
    session: Session,
    *,
    stalled_pipelines: list[dict[str, Any]],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Watchdog hook — attempt saturation for tenants with stalled TCRE waits."""
    outcomes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in stalled_pipelines[: max(1, int(limit))]:
        tid_raw = item.get("tenant_id")
        prid_raw = item.get("pipeline_run_id")
        if not tid_raw or tid_raw in seen:
            continue
        seen.add(str(tid_raw))
        try:
            tid = uuid.UUID(str(tid_raw))
            prid = uuid.UUID(str(prid_raw)) if prid_raw else None
        except ValueError:
            continue
        out = run_tcre_saturation_schedule_pass_v1(
            session,
            tenant_id=tid,
            pipeline_run_id=prid,
            trigger=TCRE_SATURATION_TRIGGER_WATCHDOG_V1,
            skip_if_saturated=True,
        )
        outcomes.append(out)
    return outcomes


def build_substrate_tcre_saturation_scheduling_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_tcre_saturation_runtime_schema_version": int(
            PHASE085_TCRE_SATURATION_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_TCRE_SATURATION_SPEC_REF_V1,
        "primary_gate_id": GP085_TCRE01_GATE_ID_V1,
        "saturation_threshold": get_tcre_saturation_threshold_v1(),
        "jobs_per_hour": get_tcre_saturation_jobs_per_hour_v1(),
        "max_queued_jobs": get_tcre_saturation_max_queued_jobs_v1(),
        "pass_max_jobs": get_tcre_saturation_pass_max_jobs_v1(),
        "celery_task_name": CELERY_TCRE_SATURATION_SCHEDULE_TASK_NAME_V1,
        "scheduler_entrypoint": "schedule_tcre_saturation_for_tenant_v1",
        "pass_entrypoint": "run_tcre_saturation_schedule_pass_v1",
        "schedule_triggers": [
            TCRE_SATURATION_TRIGGER_AFTER_PHASE_06_V1,
            TCRE_SATURATION_TRIGGER_WATCHDOG_V1,
            TCRE_SATURATION_TRIGGER_MANUAL_V1,
        ],
        "pipeline_scope_field": "substrate_pipeline_run_id",
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling"
        ),
    }


def verify_gp085_tcre01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_tcre_saturation_scheduling_catalog_v1()
    if cat["primary_gate_id"] != GP085_TCRE01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if cat["saturation_threshold"] < 0.5:
        errors.append("saturation_threshold_too_low")

    scope_src = inspect.getsource(_build_saturation_job_scope_v1)
    if "substrate_pipeline_run_id" not in scope_src:
        errors.append("pipeline_scope_missing")
    pass_src = inspect.getsource(run_tcre_saturation_schedule_pass_v1)
    if "random" in pass_src.lower():
        errors.append("probabilistic_scheduling_forbidden")

    from vector.domains.cortex.reasoning.runtime import runtime_scope as rs

    norm_src = inspect.getsource(rs.normalize_reconstruction_scope_v1)
    if "substrate_pipeline_run_id" not in norm_src:
        errors.append("normalize_scope_missing_pipeline_run_id")

    from vector.domains.cortex.substrate_pipeline import phase_runners as pr

    if "run_tcre_saturation_after_phase06_v1" not in inspect.getsource(pr.run_phase_06_tcre_v1):
        errors.append("phase_06_missing_saturation_hook")

    from vector.domains.cortex.substrate_pipeline import stalled_pipeline_recovery as spr

    if "run_tcre_saturation_watchdog_hook_v1" not in inspect.getsource(
        spr.run_stalled_pipeline_watchdog_v1
    ):
        errors.append("watchdog_missing_saturation_hook")

    try:
        from app.celery_app import celery_app

        if CELERY_TCRE_SATURATION_SCHEDULE_TASK_NAME_V1 not in celery_app.tasks:
            import importlib

            importlib.import_module("app.tasks.cortex_substrate_tcre_saturation_scheduling")
        if CELERY_TCRE_SATURATION_SCHEDULE_TASK_NAME_V1 not in celery_app.tasks:
            errors.append("celery_task_not_registered")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"celery_import:{exc}")

    passed = not errors
    return {
        "id": GP085_TCRE01_GATE_ID_V1,
        "name": "cesp_substrate_tcre_saturation_scheduling",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
