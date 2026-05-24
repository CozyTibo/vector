"""Unified operator actions (R2) — pipeline run, execution commands, retrieval bootstrap."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.admin_commands import (
    clear_derived_execution_outputs_v1,
    restart_execution_from_phase_v1,
)
from vector.domains.cortex.execution.fsm import record_execution_transition_v1
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.pipeline.operator_admin_overview import invalidate_operator_overview_cache_v1
from vector.domains.cortex.pipeline.operator_admin_runtime import invalidate_operator_runtime_cache_v1
from vector.domains.cortex.pipeline.pipeline_admin_run import (
    CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE,
    CORTEX_FLUSH_RERUN_CONFIRM_PHRASE,
    CORTEX_MANUAL_SYNC_CONFIRM_PHRASE,
    pipeline_run_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    bootstrap_retrieval_index_from_upstream_v1,
)
from vector.domains.cortex.retrieval.retrieval_operator_workflows import (
    RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_recovery import (
    RecoveryStrategyV1,
    recover_continuity_p0_pipeline_v1,
)
from vector.settings import Settings

OperatorActionKind = Literal[
    "run_from_ingestion",
    "run_from_phase",
    "restart_execution",
    "clear_derived",
    "flush_derived",
    "flush_all",
    "rebuild_retrieval_index",
    "p0_recover",
]

CORTEX_RESTART_EXECUTION_CONFIRM_PHRASE = "RESTART CORTEX EXECUTION FROM PHASE"
CORTEX_CLEAR_DERIVED_CONFIRM_PHRASE = "CLEAR DERIVED CORTEX EXECUTION OUTPUTS"
CONTINUITY_P0_RECOVER_CONFIRM_PHRASE = "RECOVER CONTINUITY P0 PIPELINE"

_START_PHASE_TO_API: dict[str, str] = {
    "canonical": "CANONICAL",
    "identity": "IDENTITY",
    "graph": "GRAPH",
    "reconstruction": "TCRE",
    "retrieval": "RETRIEVAL",
    "synthesis": "SYNTHESIS",
}


def invalidate_operator_caches_v1(tenant_id: uuid.UUID) -> None:
    invalidate_operator_overview_cache_v1(tenant_id)
    invalidate_operator_runtime_cache_v1(tenant_id)


def _require_confirmation(actual: str | None, expected: str) -> None:
    if (actual or "").strip() != expected:
        raise ValueError("confirmation_mismatch")


def _resolve_from_phase(*, start_phase: str | None, from_phase: str | None) -> str:
    if from_phase and from_phase.strip():
        return from_phase.strip().upper()
    key = (start_phase or "").strip().lower()
    api_phase = _START_PHASE_TO_API.get(key)
    if api_phase is None:
        raise ValueError(f"unsupported_start_phase:{start_phase or from_phase}")
    return api_phase


def _audit_operator_action_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    action: str,
    pipeline_run_id: uuid.UUID | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    fsm = (lease.fsm_state if lease is not None else None) or "UNKNOWN"
    run_id = pipeline_run_id or (lease.pipeline_run_id if lease is not None else None)
    record_execution_transition_v1(
        session,
        tenant_id=tenant_id,
        from_state=fsm[:64],
        to_state=fsm[:64],
        trigger=f"operator_action:{action}"[:128],
        pipeline_run_id=run_id,
        gate_result="operator",
        detail={"action": action, **(detail or {})},
    )


def execute_operator_action_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    action: OperatorActionKind,
    start_phase: str | None = None,
    from_phase: str | None = None,
    confirmation: str | None = None,
    force: bool = False,
    break_glass: bool = False,
    scope: str | None = None,
    pipeline_run_id: uuid.UUID | None = None,
    p0_strategy: RecoveryStrategyV1 = "new_run",
    source_pipeline_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Dispatch one operator action; caller must commit session."""
    result: dict[str, Any]

    if action == "run_from_ingestion":
        _require_confirmation(confirmation, CORTEX_MANUAL_SYNC_CONFIRM_PHRASE)
        result = pipeline_run_v1(
            session,
            settings,
            tenant_id=tenant_id,
            mode="from_ingestion",
            confirmation=confirmation,
        )
    elif action == "run_from_phase":
        result = pipeline_run_v1(
            session,
            settings,
            tenant_id=tenant_id,
            mode="from_phase",
            start_phase=start_phase,
        )
    elif action == "restart_execution":
        _require_confirmation(confirmation, CORTEX_RESTART_EXECUTION_CONFIRM_PHRASE)
        api_phase = _resolve_from_phase(start_phase=start_phase, from_phase=from_phase)
        result = restart_execution_from_phase_v1(
            session,
            tenant_id=tenant_id,
            from_phase=api_phase,
            pipeline_run_id=pipeline_run_id,
            force=force,
            break_glass=break_glass,
        )
    elif action == "clear_derived":
        _require_confirmation(confirmation, CORTEX_CLEAR_DERIVED_CONFIRM_PHRASE)
        api_phase = _resolve_from_phase(start_phase=start_phase, from_phase=from_phase)
        result = clear_derived_execution_outputs_v1(
            session,
            tenant_id=tenant_id,
            from_phase=api_phase,
            scope=scope,
            flush_all=False,
        )
    elif action == "flush_derived":
        _require_confirmation(confirmation, CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE)
        result = pipeline_run_v1(
            session,
            settings,
            tenant_id=tenant_id,
            mode="flush_and_run",
            flush_mode="derived_only",
            confirmation=confirmation,
        )
    elif action == "flush_all":
        _require_confirmation(confirmation, CORTEX_FLUSH_RERUN_CONFIRM_PHRASE)
        result = pipeline_run_v1(
            session,
            settings,
            tenant_id=tenant_id,
            mode="flush_and_run",
            flush_mode="all",
            confirmation=confirmation,
        )
    elif action == "rebuild_retrieval_index":
        _require_confirmation(confirmation, RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1)
        result = bootstrap_retrieval_index_from_upstream_v1(session, tenant_id=tenant_id)
    elif action == "p0_recover":
        _require_confirmation(confirmation, CONTINUITY_P0_RECOVER_CONFIRM_PHRASE)
        result = recover_continuity_p0_pipeline_v1(
            session,
            tenant_id=tenant_id,
            strategy=p0_strategy,
            source_pipeline_run_id=source_pipeline_run_id,
        )
        if not result.get("recovered"):
            raise ValueError("p0_recover_failed")
    else:
        raise ValueError(f"unsupported_action:{action}")

    _audit_operator_action_v1(
        session,
        tenant_id=tenant_id,
        action=action,
        pipeline_run_id=pipeline_run_id,
        detail={"ok": True},
    )
    invalidate_operator_caches_v1(tenant_id)
    return {
        "surface_kind": "operator_action_v1",
        "action": action,
        "tenant_id": str(tenant_id),
        "result": result,
    }
