"""M0 shadow metrics: which orchestration authority drove substrate work for a tenant.

Structured log event ``cortex_execution_path`` with ``execution_path`` in:
``convergence`` | ``legacy`` | ``progression`` | ``admin_bypass``.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Final

_LOGGER = logging.getLogger(__name__)

EXECUTION_PATH_CONVERGENCE: Final[str] = "convergence"
EXECUTION_PATH_LEGACY: Final[str] = "legacy"
EXECUTION_PATH_PROGRESSION: Final[str] = "progression"
EXECUTION_PATH_ADMIN_BYPASS: Final[str] = "admin_bypass"

_VALID_EXECUTION_PATHS: Final[frozenset[str]] = frozenset(
    {
        EXECUTION_PATH_CONVERGENCE,
        EXECUTION_PATH_LEGACY,
        EXECUTION_PATH_PROGRESSION,
        EXECUTION_PATH_ADMIN_BYPASS,
    }
)

EXECUTION_PATH_TELEMETRY_SCHEMA_VERSION: Final[int] = 1
EXECUTION_PATH_TELEMETRY_EVENT: Final[str] = "cortex_execution_path"


def execution_path_from_post_ingestion_path(path: str | None) -> str:
    """Map post-ingestion dispatch ``path`` field to M0 ``execution_path``."""
    normalized = (path or "").strip()
    if normalized == "convergence_lease":
        return EXECUTION_PATH_CONVERGENCE
    if normalized == "legacy_debounced_coordinator":
        return EXECUTION_PATH_LEGACY
    return EXECUTION_PATH_LEGACY


def emit_execution_path_telemetry_v1(
    *,
    tenant_id: uuid.UUID | str,
    execution_path: str,
    trigger: str,
    pipeline_run_id: uuid.UUID | str | None = None,
    phase_id: str | None = None,
    celery_task_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit one M0 shadow-metric event (structured log + return payload for callers/tests)."""
    if execution_path not in _VALID_EXECUTION_PATHS:
        msg = f"invalid_execution_path:{execution_path}"
        raise ValueError(msg)
    tid = str(tenant_id)
    payload: dict[str, Any] = {
        "event": EXECUTION_PATH_TELEMETRY_EVENT,
        "schema_version": EXECUTION_PATH_TELEMETRY_SCHEMA_VERSION,
        "tenant_id": tid,
        "execution_path": execution_path,
        "trigger": (trigger or "unknown")[:256],
    }
    if pipeline_run_id is not None:
        payload["pipeline_run_id"] = str(pipeline_run_id)
    if phase_id is not None:
        payload["phase_id"] = phase_id
    if celery_task_id is not None:
        payload["celery_task_id"] = celery_task_id
    if detail:
        payload["detail"] = detail
    _LOGGER.info(
        "%s tenant_id=%s execution_path=%s trigger=%s pipeline_run_id=%s phase_id=%s "
        "celery_task_id=%s",
        EXECUTION_PATH_TELEMETRY_EVENT,
        tid,
        execution_path,
        payload["trigger"],
        payload.get("pipeline_run_id"),
        payload.get("phase_id"),
        payload.get("celery_task_id"),
        extra={"cortex_execution_path_telemetry": payload},
    )
    return payload


def emit_admin_bypass_telemetry_v1(
    *,
    tenant_id: uuid.UUID | str,
    admin_action: str,
    pipeline_run_id: uuid.UUID | str | None = None,
    celery_task_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Admin endpoints that mutate substrate state outside the tenant execution FSM."""
    merged_detail = {"admin_action": (admin_action or "unknown")[:128]}
    if detail:
        merged_detail.update(detail)
    return emit_execution_path_telemetry_v1(
        tenant_id=tenant_id,
        execution_path=EXECUTION_PATH_ADMIN_BYPASS,
        trigger=f"admin:{admin_action}",
        pipeline_run_id=pipeline_run_id,
        celery_task_id=celery_task_id,
        detail=merged_detail,
    )
