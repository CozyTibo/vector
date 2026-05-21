"""Phase 08.5 P085-09 — substrate continuity watchdog (**G-P085-WATCH-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-recovery-continuity-doctrine.md`` §Watchdog.
Runtime: ``run_stalled_pipeline_watchdog_v1``; Celery beat uses convergence sweep only (M3).
"""

from __future__ import annotations

import inspect
import os
from datetime import UTC, datetime
from typing import Any, Final

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

PHASE085_CONTINUITY_WATCHDOG_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_CONTINUITY_WATCHDOG_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-recovery-continuity-doctrine.md"
)

GP085_WATCH01_GATE_ID_V1: Final[str] = "G-P085-WATCH-01"

CELERY_CONTINUITY_WATCHDOG_TASK_NAME_V1: Final[str] = (
    "vector.cortex.substrate_pipeline.continuity_watchdog"
)

CELERY_BEAT_SCHEDULE_KEY_V1: Final[str] = "cortex-substrate-continuity-watchdog"

DEFAULT_WATCHDOG_INTERVAL_SECONDS_V1: Final[int] = 600

WATCHDOG_ALGORITHM_STEP_IDS_V1: Final[tuple[str, ...]] = (
    "WATCH-01-LIST-STALE",
    "WATCH-02-MARK-STALLED",
    "WATCH-03-AUTO-RECOVER",
    "WATCH-04-AUDIT-METRIC",
)

AUTO_RECOVERY_ORDER_V1: Final[tuple[str, ...]] = (
    "phase_07_complete_mark_continuation_complete",
    "tcre_completed_execution_lease_resume",
    "rebind_latest_completed_tcre",
    "re_enqueue_phase_06_bounded",
    "dlq_operator_alert",
)

_WATCHDOG_METRIC_NAMES_V1: Final[tuple[str, ...]] = (
    "substrate_watchdog_tick_total",
    "substrate_watchdog_stalls_detected_total",
    "substrate_watchdog_recoveries_attempted_total",
    "substrate_watchdog_recoveries_succeeded_total",
    "substrate_watchdog_recoveries_failed_total",
)

_WATCHDOG_METRICS_V1: dict[str, int] = {name: 0 for name in _WATCHDOG_METRIC_NAMES_V1}


class SubstrateContinuityWatchdogError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def increment_watchdog_metric_v1(metric_name: str, *, delta: int = 1) -> None:
    if metric_name in _WATCHDOG_METRICS_V1:
        _WATCHDOG_METRICS_V1[metric_name] += max(1, int(delta))


def snapshot_watchdog_metrics_v1() -> dict[str, int]:
    return dict(_WATCHDOG_METRICS_V1)


def get_watchdog_interval_seconds_v1() -> int:
    """Configured Celery beat interval (default **600s**)."""
    raw = os.environ.get("CORTEX_SUBSTRATE_CONTINUITY_WATCHDOG_INTERVAL_SECONDS")
    if raw:
        return max(120, int(raw))
    try:
        from vector.settings import get_settings

        return max(120, int(get_settings().cortex_substrate_continuity_watchdog_interval_seconds))
    except Exception:  # noqa: BLE001
        return DEFAULT_WATCHDOG_INTERVAL_SECONDS_V1


def get_watchdog_stall_threshold_seconds_v1() -> int:
    try:
        from vector.settings import get_settings

        return int(get_settings().cortex_substrate_continuation_stall_seconds)
    except Exception:  # noqa: BLE001
        return 1800


def get_watchdog_auto_recover_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_substrate_continuation_auto_recover)
    except Exception:  # noqa: BLE001
        return True


def compute_watchdog_run_digest_v1(
    *,
    watchdog_run_id: str,
    stall_threshold_seconds: int,
    auto_recover: bool,
    stalled_count: int,
    recoveries_succeeded: int,
    recoveries_failed: int,
) -> str:
    return hash_reasoning_canonical_json_sha256_v1(
        {
            "watchdog_run_id": watchdog_run_id,
            "stall_threshold_seconds": stall_threshold_seconds,
            "auto_recover": auto_recover,
            "stalled_count": stalled_count,
            "recoveries_succeeded": recoveries_succeeded,
            "recoveries_failed": recoveries_failed,
            "purpose": "substrate_continuity_watchdog_run_v1",
        }
    )


def build_watchdog_audit_record_v1(
    *,
    watchdog_run_id: str,
    stall_threshold_seconds: int,
    auto_recover: bool,
    stalled: list[dict[str, Any]],
    recovered: list[dict[str, Any]],
    started_at: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    """Structured audit log payload for one watchdog tick (**G-P085-WATCH-01**)."""
    succeeded = sum(1 for r in recovered if r.get("recovered"))
    failed = len(recovered) - succeeded
    digest = compute_watchdog_run_digest_v1(
        watchdog_run_id=watchdog_run_id,
        stall_threshold_seconds=stall_threshold_seconds,
        auto_recover=auto_recover,
        stalled_count=len(stalled),
        recoveries_succeeded=succeeded,
        recoveries_failed=failed,
    )
    return {
        "schema_version": PHASE085_CONTINUITY_WATCHDOG_RUNTIME_SCHEMA_VERSION,
        "watchdog_run_id": watchdog_run_id,
        "gate_id": GP085_WATCH01_GATE_ID_V1,
        "celery_task_name": CELERY_CONTINUITY_WATCHDOG_TASK_NAME_V1,
        "stall_threshold_seconds": int(stall_threshold_seconds),
        "auto_recover": bool(auto_recover),
        "stalled_count": len(stalled),
        "recoveries_attempted": len(recovered),
        "recoveries_succeeded": succeeded,
        "recoveries_failed": failed,
        "watchdog_run_digest": f"sha256:{digest}",
        "started_at": started_at or datetime.now(UTC).isoformat(),
        "completed_at": completed_at or datetime.now(UTC).isoformat(),
        "stalled_pipeline_run_ids": [s.get("pipeline_run_id") for s in stalled],
        "recovery_results": recovered,
    }


def build_substrate_continuity_watchdog_catalog_v1() -> dict[str, Any]:
    """Doctrine catalog for continuity watchdog (P085-09)."""
    env_interval = int(
        os.environ.get(
            "CORTEX_SUBSTRATE_CONTINUITY_WATCHDOG_INTERVAL_SECONDS",
            str(DEFAULT_WATCHDOG_INTERVAL_SECONDS_V1),
        )
    )
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_continuity_watchdog_runtime_schema_version": int(
            PHASE085_CONTINUITY_WATCHDOG_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_CONTINUITY_WATCHDOG_SPEC_REF_V1,
        "primary_gate_id": GP085_WATCH01_GATE_ID_V1,
        "celery_task_name": CELERY_CONTINUITY_WATCHDOG_TASK_NAME_V1,
        "celery_beat_schedule_key": CELERY_BEAT_SCHEDULE_KEY_V1,
        "default_interval_seconds": int(DEFAULT_WATCHDOG_INTERVAL_SECONDS_V1),
        "configured_interval_seconds": get_watchdog_interval_seconds_v1(),
        "env_interval_seconds": max(120, env_interval),
        "stall_threshold_seconds": get_watchdog_stall_threshold_seconds_v1(),
        "auto_recover_enabled": get_watchdog_auto_recover_enabled_v1(),
        "algorithm_step_ids": list(WATCHDOG_ALGORITHM_STEP_IDS_V1),
        "algorithm_steps": [
            {
                "step_id": "WATCH-01-LIST-STALE",
                "description": "list_stale_waiting_continuations_v1(T_stall)",
            },
            {
                "step_id": "WATCH-02-MARK-STALLED",
                "description": "Mark STALLED, recovery_required=true",
            },
            {
                "step_id": "WATCH-03-AUTO-RECOVER",
                "description": "recover_stalled_pipeline_v1(action=auto) when enabled",
            },
            {
                "step_id": "WATCH-04-AUDIT-METRIC",
                "description": "Emit audit log + operational metrics",
            },
        ],
        "auto_recovery_order": list(AUTO_RECOVERY_ORDER_V1),
        "runtime_entrypoints": [
            "vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery."
            "run_stalled_pipeline_watchdog_v1",
        ],
        "operational_metrics": list(_WATCHDOG_METRIC_NAMES_V1),
        "operational_metrics_snapshot": snapshot_watchdog_metrics_v1(),
    }


def verify_gp085_watch01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_continuity_watchdog_catalog_v1()
    if cat["primary_gate_id"] != GP085_WATCH01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if int(cat["default_interval_seconds"]) != DEFAULT_WATCHDOG_INTERVAL_SECONDS_V1:
        errors.append("default_interval_not_600")

    from vector.domains.cortex.convergence.scheduling import (
        convergence_runtime_authoritative_v1,
        verify_convergence_sweep_in_celery_beat_v1,
    )
    if convergence_runtime_authoritative_v1():
        errors.extend(verify_convergence_sweep_in_celery_beat_v1())
        from vector.domains.cortex.ingestion import post_ingestion_refresh_dispatch as pid

        dispatch_src = inspect.getsource(pid.schedule_post_ingestion_substrate_refresh)
        if "mark_tenant_dirty_v1" not in dispatch_src:
            errors.append("post_ingestion_missing_convergence_dirty_mark")
    else:
        from app.celery_app import celery_app

        beat = dict(celery_app.conf.beat_schedule or {})
        entry = beat.get(CELERY_BEAT_SCHEDULE_KEY_V1)
        if entry is None:
            errors.append("celery_beat_schedule_missing")
        elif str(entry.get("task")) != CELERY_CONTINUITY_WATCHDOG_TASK_NAME_V1:
            errors.append("celery_beat_task_name_mismatch")

    from vector.domains.cortex.substrate_pipeline import stalled_pipeline_recovery as rec_mod

    detect_src = inspect.getsource(rec_mod.detect_stalled_substrate_pipelines_v1)
    if "list_stalled_continuations_v1" not in detect_src:
        errors.append("detect_missing_list_stale_waiting")

    watch_src = inspect.getsource(rec_mod.run_stalled_pipeline_watchdog_v1)
    for needle in (
        "detect_stalled_substrate_pipelines_v1",
        "recover_stalled_pipeline_v1",
        "build_watchdog_audit_record_v1",
    ):
        if needle not in watch_src:
            errors.append(f"watchdog_missing:{needle}")

    import importlib.util

    if importlib.util.find_spec("app.tasks.cortex_substrate_continuity_watchdog") is not None:
        errors.append("celery_continuity_watchdog_module_must_be_deleted_m9")

    passed = not errors
    return {
        "id": GP085_WATCH01_GATE_ID_V1,
        "name": "cesp_substrate_continuity_watchdog",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
