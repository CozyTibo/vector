"""Tenant execution scheduling helpers (authoritative beat + ingest path)."""

from __future__ import annotations

import inspect
import os
from typing import Final

from vector.settings import Settings

CELERY_CONVERGENCE_SWEEP_BEAT_KEY_V1: Final[str] = "cortex-convergence-sweep"
CELERY_CONVERGENCE_SWEEP_TASK_NAME_V1: Final[str] = "vector.cortex.convergence.sweep"
CELERY_CONVERGENCE_RUN_TASK_NAME_V1: Final[str] = "vector.cortex.convergence.run_tenant"
CELERY_EXECUTION_SLICE_TASK_NAME_V1: Final[str] = "vector.cortex.execution.run_slice"


def _env_flag(name: str, *, default: str = "true") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


def convergence_runtime_authoritative_v1(settings: Settings | None = None) -> bool:
    """True when execution sweeper is enabled (sole periodic substrate scheduler after M3)."""
    if settings is None:
        return _env_flag("CORTEX_CONVERGENCE_SWEEPER_ENABLED")
    return bool(settings.cortex_convergence_sweeper_enabled)


execution_runtime_authoritative_v1 = convergence_runtime_authoritative_v1


LEGACY_SUBSTRATE_BEAT_TASK_NAMES_V1: Final[tuple[str, ...]] = (
    "vector.cortex.substrate_pipeline.continuity_watchdog",
    "vector.cortex.operational_runtime.substrate_progression_tick",
)


def verify_legacy_substrate_beats_absent_from_celery_beat_v1() -> list[str]:
    """Return error codes if legacy watchdog/progression ticks are still on Celery beat (M3)."""
    from app.celery_app import celery_app

    errors: list[str] = []
    beat = dict(celery_app.conf.beat_schedule or {})
    for task_name in LEGACY_SUBSTRATE_BEAT_TASK_NAMES_V1:
        for key, entry in beat.items():
            if str(entry.get("task")) == task_name:
                errors.append(f"legacy_substrate_beat_still_registered:{key}:{task_name}")
    return errors


def verify_convergence_sweep_in_celery_beat_v1() -> list[str]:
    """Return error codes if execution sweeper is not registered in beat schedule."""
    from app.celery_app import celery_app
    from app.tasks import cortex_execution as exec_mod

    errors: list[str] = []
    errors.extend(verify_no_legacy_phase_chain_v1())
    beat = dict(celery_app.conf.beat_schedule or {})
    entry = beat.get(CELERY_CONVERGENCE_SWEEP_BEAT_KEY_V1)
    if entry is None:
        errors.append("convergence_sweep_beat_missing")
    elif str(entry.get("task")) != CELERY_CONVERGENCE_SWEEP_TASK_NAME_V1:
        errors.append("convergence_sweep_beat_task_mismatch")

    slice_src = inspect.getsource(exec_mod.run_execution_slice_task)
    if "run_tenant_convergence_v1" not in slice_src:
        errors.append("execution_slice_task_missing_runner")
    errors.extend(verify_legacy_substrate_beats_absent_from_celery_beat_v1())
    errors.extend(verify_tenant_execution_fsm_on_lease_v1())
    return errors


def verify_schedule_substrate_pipeline_uses_convergence_v1() -> list[str]:
    """Return error codes if legacy coordinator scheduling remains in orchestrator (M4)."""
    from vector.domains.cortex.substrate_pipeline import orchestrator as orch

    errors: list[str] = []
    src = inspect.getsource(orch.schedule_substrate_pipeline_v1)
    if "run_cortex_substrate_pipeline_coordinator_task" in src:
        errors.append("schedule_substrate_pipeline_enqueues_legacy_coordinator")
    if "enqueue_tenant_convergence_v1" not in src:
        errors.append("schedule_substrate_pipeline_missing_convergence_enqueue")
    if "mark_tenant_dirty_v1" not in src:
        errors.append("schedule_substrate_pipeline_missing_dirty_mark")
    return errors


def verify_tenant_execution_fsm_on_lease_v1() -> list[str]:
    """Return error codes if M5 FSM is not wired on execution lease (M5)."""
    from vector.domains.cortex.execution import lease as lease_mod

    errors: list[str] = []
    model_path = (
        "vector.infrastructure.db.models.cortex_tenant_convergence_lease."
        "CortexTenantConvergenceLease"
    )
    try:
        from vector.infrastructure.db.models.cortex_tenant_convergence_lease import (
            CortexTenantConvergenceLease,
        )
    except ImportError:
        errors.append("tenant_execution_lease_model_missing")
        return errors
    if not hasattr(CortexTenantConvergenceLease, "fsm_state"):
        errors.append("tenant_execution_lease_missing_fsm_state_column")
    dirty_src = inspect.getsource(lease_mod.mark_tenant_dirty_v1)
    if "apply_fsm_transition_v1" not in dirty_src:
        errors.append("mark_dirty_missing_fsm_transition")
    from vector.domains.cortex.execution import fsm as fsm_mod

    if "record_execution_transition_v1" not in inspect.getsource(fsm_mod):
        errors.append("fsm_missing_transition_log_writer")
    return errors


def verify_no_legacy_phase_chain_v1() -> list[str]:
    """Return error codes if M6 legacy phase chaining remains (M6)."""
    from vector.domains.cortex.substrate_pipeline import orchestrator as orch

    errors: list[str] = []
    if hasattr(orch, "chain_after_phase_v1"):
        errors.append("chain_after_phase_v1_still_exported")
    enqueue_src = inspect.getsource(orch.enqueue_next_pipeline_phase_v1)
    if "run_cortex_substrate_pipeline_phase_task" in enqueue_src:
        errors.append("enqueue_next_still_uses_phase_celery_task")
    if "enqueue_execution_slice_at_phase_v1" not in enqueue_src:
        errors.append("enqueue_next_missing_execution_slice_redirect")
    from vector.domains.cortex.execution import enqueue as enqueue_mod

    if "run_execution_slice_task" not in inspect.getsource(enqueue_mod.enqueue_tenant_convergence_v1):
        errors.append("enqueue_missing_execution_slice_task")
    return errors
