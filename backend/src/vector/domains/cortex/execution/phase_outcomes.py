"""Execution-facing mapping for substrate phase receipt outcomes (TRUE P0B)."""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_BLOCKED,
    PHASE_OUTCOME_COMPLETED,
    PHASE_OUTCOME_COMPLETED_EMPTY,
    PHASE_OUTCOME_FAILED,
    PHASE_OUTCOME_SKIPPED_BY_POLICY,
    PHASE_OUTCOME_WAITING_ASYNC,
    read_phase_receipt_from_output,
)

WORKER_OUTCOME_CONVERGED: Final[str] = "converged_slice"
WORKER_OUTCOME_WAITING_TCRE: Final[str] = "waiting_on_tcre"
WORKER_OUTCOME_BLOCKED_RETRIEVAL: Final[str] = "blocked_retrieval_starvation"
WORKER_OUTCOME_CANONICAL_TOPOLOGY_WAIT: Final[str] = "canonical_topology_wait"
WORKER_OUTCOME_CANONICAL_PARTIAL: Final[str] = "canonical_partial"
WORKER_OUTCOME_TIME_BUDGET: Final[str] = "time_budget_requeue"
WORKER_OUTCOME_STALLED: Final[str] = "execution_stalled"


def store_last_phase_receipt_on_lease_v1(lease: Any, *, phase_output: dict[str, Any]) -> None:
    """Persist receipt pointers on lease detail_json for operator surfaces."""
    rec = read_phase_receipt_from_output(phase_output)
    detail = dict(lease.detail_json or {})
    if rec:
        detail["last_phase_receipt_hash"] = rec.get("receipt_hash")
        detail["last_phase_outcome"] = rec.get("outcome")
        detail["last_phase_id"] = rec.get("phase_id")
        if rec.get("blocked_reason"):
            detail["last_blocked_reason"] = rec.get("blocked_reason")
    elif phase_output.get("receipt_hash"):
        detail["last_phase_receipt_hash"] = phase_output.get("receipt_hash")
        detail["last_phase_outcome"] = phase_output.get("outcome")
    lease.detail_json = detail


def phase_outcome_from_output_v1(output: dict[str, Any] | None) -> str | None:
    rec = read_phase_receipt_from_output(output)
    if rec:
        return str(rec.get("outcome") or "") or None
    out = output or {}
    oc = out.get("outcome")
    return str(oc) if oc else None


def is_topology_blocked_phase02_v1(output: dict[str, Any]) -> bool:
    oc = phase_outcome_from_output_v1(output)
    if oc == PHASE_OUTCOME_BLOCKED:
        br = (output or {}).get("blocked_reason") or ""
        rec = read_phase_receipt_from_output(output) or {}
        br = br or str(rec.get("blocked_reason") or "")
        return "topology" in br.lower()
    return False


def is_waiting_async_phase06_v1(output: dict[str, Any]) -> bool:
    return phase_outcome_from_output_v1(output) == PHASE_OUTCOME_WAITING_ASYNC


def worker_outcome_label_for_phase02_continue_v1(
    *,
    phase_output: dict[str, Any],
    canonical_summary: dict[str, Any],
) -> str:
    if is_topology_blocked_phase02_v1(phase_output):
        progress_made = bool(canonical_summary.get("progress_made"))
        if not progress_made:
            return WORKER_OUTCOME_CANONICAL_TOPOLOGY_WAIT
        return WORKER_OUTCOME_CANONICAL_PARTIAL
    oc = phase_outcome_from_output_v1(phase_output)
    if oc in (PHASE_OUTCOME_COMPLETED, PHASE_OUTCOME_COMPLETED_EMPTY):
        return WORKER_OUTCOME_CONVERGED
    if oc == PHASE_OUTCOME_FAILED:
        return WORKER_OUTCOME_STALLED
    return WORKER_OUTCOME_CANONICAL_PARTIAL


def execution_stop_is_terminal_blocked_v1(*, fsm_state: str, block_reason_code: str | None) -> bool:
    from vector.domains.cortex.execution.tenant_constants import FSM_BLOCKED

    return fsm_state == FSM_BLOCKED and bool((block_reason_code or "").strip())

