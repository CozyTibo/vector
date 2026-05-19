"""Convergence runtime scheduling helpers (authoritative beat + ingest path)."""

from __future__ import annotations

import inspect
import os
from typing import Final

from vector.settings import Settings

CELERY_CONVERGENCE_SWEEP_BEAT_KEY_V1: Final[str] = "cortex-convergence-sweep"
CELERY_CONVERGENCE_SWEEP_TASK_NAME_V1: Final[str] = "vector.cortex.convergence.sweep"
CELERY_CONVERGENCE_RUN_TASK_NAME_V1: Final[str] = "vector.cortex.convergence.run_tenant"


def _env_flag(name: str, *, default: str = "true") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


def convergence_runtime_authoritative_v1(settings: Settings | None = None) -> bool:
    """True when Postgres lease + sweeper replace legacy debounce coordinator scheduling.

    Uses ``os.environ`` when *settings* is omitted so static gates match ``celery_app`` beat
    construction without requiring a full Settings load (e.g. in unit tests).
    """
    if settings is None:
        return (
            _env_flag("CORTEX_CONVERGENCE_RUNTIME_ENABLED")
            and _env_flag("CORTEX_CONVERGENCE_SWEEPER_ENABLED")
            and _env_flag("CORTEX_CONVERGENCE_DISABLE_LEGACY_PROGRESSION_BEAT")
        )
    return bool(
        settings.cortex_convergence_runtime_enabled
        and settings.cortex_convergence_sweeper_enabled
        and settings.cortex_convergence_disable_legacy_progression_beat
    )


def verify_convergence_sweep_in_celery_beat_v1() -> list[str]:
    """Return error codes if convergence sweeper is not registered in beat schedule."""
    from app.celery_app import celery_app
    from app.tasks import cortex_convergence as conv_mod

    errors: list[str] = []
    beat = dict(celery_app.conf.beat_schedule or {})
    entry = beat.get(CELERY_CONVERGENCE_SWEEP_BEAT_KEY_V1)
    if entry is None:
        errors.append("convergence_sweep_beat_missing")
    elif str(entry.get("task")) != CELERY_CONVERGENCE_SWEEP_TASK_NAME_V1:
        errors.append("convergence_sweep_beat_task_mismatch")

    sweep_src = inspect.getsource(conv_mod.run_convergence_sweep_task)
    if "run_convergence_sweep_v1" not in sweep_src:
        errors.append("convergence_sweep_task_missing_runner")
    run_src = inspect.getsource(conv_mod.run_tenant_convergence_task)
    if "run_tenant_convergence_v1" not in run_src:
        errors.append("convergence_run_task_missing_runner")
    return errors
