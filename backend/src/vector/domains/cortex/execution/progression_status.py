"""Read-only substrate progression status and retrieval outcome classification (M7).

Autonomous closure runs in ``run_tenant_execution_v1``; operators use
``admin_rerun_substrate_execution_v1`` for manual recovery.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import PHASE085_NORMATIVE_TREE_V1
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_eligible_scopes_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    PHASE_STATUS_COMPLETED,
    PHASE_STATUS_SKIPPED,
    PIPELINE_STATUS_COMPLETED,
    PIPELINE_STATUS_RUNNING,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    get_continuation_for_pipeline_v1,
)
from vector.domains.cortex.execution.tenant_constants import LEASE_STATUS_WAITING
from vector.domains.cortex.substrate_pipeline.repository import (
    get_phase_run_v1,
    get_running_pipeline_run_v1,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun

PHASE085_SUBSTRATE_PROGRESSION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_SUBSTRATE_PROGRESSION_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-substrate-continuity-doctrine.md"
)

GP085_PROG_CLOSE_GATE_ID_V1: Final[str] = "G-P085-PROG-CLOSE"

EXECUTION_OWNER_ID_V1: Final[str] = "TenantExecutionLease"

MAX_RETRIEVAL_MATERIALIZATION_RETRIES_V1: Final[int] = 3

TENANT_PROGRESSION_CLASS_PROGRESSING_V1: Final[str] = "progressing"
TENANT_PROGRESSION_CLASS_STALLED_V1: Final[str] = "stalled"
TENANT_PROGRESSION_CLASS_DEGRADED_V1: Final[str] = "degraded"
TENANT_PROGRESSION_CLASS_WAITING_UPSTREAM_V1: Final[str] = "waiting_upstream"
TENANT_PROGRESSION_CLASS_OPERATIONALLY_ALIVE_V1: Final[str] = "operationally_alive"
TENANT_PROGRESSION_CLASS_IDLE_V1: Final[str] = "idle"

BLOCK_REASON_RETRIEVAL_RETRY_EXHAUSTED_V1: Final[str] = "retrieval_retry_exhausted"
BLOCK_REASON_RETRIEVAL_STARVATION_V1: Final[str] = "retrieval_operational_starvation"


def classify_retrieval_materialization_outcome_v1(
    *,
    entries_materialized: int,
    entry_count: int,
    tcre_candidates: int,
    walks_candidates: int,
    org_link_candidates: int,
) -> str:
    """Truthful retrieval outcome — avoid fake-green on empty publish with upstream work pending."""
    upstream = int(tcre_candidates) + int(walks_candidates) + int(org_link_candidates)
    accepted = int(entries_materialized or entry_count or 0)
    if accepted > 0:
        return "progressing"
    if upstream > 0:
        return "operational_starvation"
    return "healthy_idle"


def phase_status_map_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for phase_id in SUBSTRATE_PIPELINE_PHASE_ORDER:
        pr = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=phase_id)
        out[phase_id] = pr.status if pr is not None else "missing"
    return out


def first_incomplete_phase_v1(phase_status: dict[str, str]) -> str | None:
    for phase_id in SUBSTRATE_PIPELINE_PHASE_ORDER:
        st = phase_status.get(phase_id)
        if st in (PHASE_STATUS_COMPLETED, PHASE_STATUS_SKIPPED):
            continue
        return phase_id
    return None


def retrieval_retry_count_v1(run: CortexSubstratePipelineRun) -> int:
    summary = dict(run.summary_json or {})
    prog = dict(summary.get("progression") or {})
    return int(prog.get("retrieval_materialization_retries") or 0)


def increment_retrieval_retry_v1(session: Session, *, run: CortexSubstratePipelineRun) -> int:
    summary = dict(run.summary_json or {})
    prog = dict(summary.get("progression") or {})
    n = int(prog.get("retrieval_materialization_retries") or 0) + 1
    prog["retrieval_materialization_retries"] = n
    prog["last_retrieval_retry_at"] = datetime.now(UTC).isoformat()
    summary["progression"] = prog
    run.summary_json = summary
    session.flush()
    return n


def record_execution_receipt_v1(
    session: Session,
    *,
    run: CortexSubstratePipelineRun,
    action: str,
    outcome: str,
    detail: dict[str, Any] | None = None,
) -> None:
    summary = dict(run.summary_json or {})
    receipts = list(summary.get("progression_receipts") or [])
    receipts.append(
        {
            "action": action,
            "outcome": outcome,
            "at": datetime.now(UTC).isoformat(),
            "detail": dict(detail or {}),
        }
    )
    summary["progression_receipts"] = receipts[-32:]
    run.summary_json = summary
    session.flush()


def build_substrate_operational_progression_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_substrate_progression_runtime_schema_version": int(
            PHASE085_SUBSTRATE_PROGRESSION_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_SUBSTRATE_PROGRESSION_SPEC_REF_V1,
        "primary_gate_id": GP085_PROG_CLOSE_GATE_ID_V1,
        "progression_owner_id": EXECUTION_OWNER_ID_V1,
        "entrypoint": "admin_rerun_substrate_execution_v1",
        "status_entrypoint": "build_substrate_progression_status_v1",
        "max_retrieval_materialization_retries": MAX_RETRIEVAL_MATERIALIZATION_RETRIES_V1,
        "blocked_fsm_state": "BLOCKED",
        "operator_playbook_ref": "DOCS/cortex/CORTEX_SIMPLIFICATION_AND_DETERMINISM_REFACTOR.md#m7-operator-playbook",
    }


def build_substrate_progression_status_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    include_legacy_continuation: bool = False,
) -> dict[str, Any]:
    """Operator-facing snapshot — lease FSM is authoritative; pipeline run is mirror."""
    run = None
    if pipeline_run_id is not None:
        run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
        if run is None or run.tenant_id != tenant_id:
            run = None
    if run is None:
        run = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    if run is None:
        run = session.scalar(
            select(CortexSubstratePipelineRun)
            .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
            .order_by(CortexSubstratePipelineRun.created_at.desc())
            .limit(1)
        )

    phase_status: dict[str, str] = {}
    continuation_payload: dict[str, Any] | None = None
    if run is not None:
        phase_status = phase_status_map_v1(session, pipeline_run_id=run.id)
    if run is not None and include_legacy_continuation:
        cont = get_continuation_for_pipeline_v1(session, pipeline_run_id=run.id)
        if cont is not None:
            continuation_payload = {
                "continuation_id": str(cont.id),
                "continuation_status": cont.continuation_status,
                "waiting_on": cont.waiting_on,
                "current_phase": cont.current_phase,
                "async_job_id": str(cont.async_job_id) if cont.async_job_id else None,
                "retry_count": int(cont.retry_count or 0),
                "recovery_required": bool(cont.recovery_required),
                "failure_reason": cont.failure_reason,
                "last_heartbeat_at": (
                    cont.last_heartbeat_at.isoformat() if cont.last_heartbeat_at else None
                ),
            }

    from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1

    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    lease_payload: dict[str, Any] | None = None
    if lease is not None:
        detail = dict(lease.detail_json or {})
        lease_payload = {
            "authoritative": True,
            "status": lease.status,
            "fsm_state": lease.fsm_state,
            "phase_cursor": lease.phase_cursor,
            "block_reason_code": lease.block_reason_code,
            "block_detail": lease.block_detail,
            "last_phase_receipt_hash": detail.get("last_phase_receipt_hash"),
            "last_phase_outcome": detail.get("last_phase_outcome"),
            "last_phase_id": detail.get("last_phase_id"),
            "pipeline_run_id": str(lease.pipeline_run_id) if lease.pipeline_run_id else None,
        }

    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    synth_scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
    index_count = int(synth_scope.get("index_row_count") or 0)
    eligible = int(synth_scope.get("eligible_scopes") or 0)

    progression_class = TENANT_PROGRESSION_CLASS_IDLE_V1
    stop_reason: str | None = None

    if lease is not None and (lease.fsm_state or "").strip() == "BLOCKED":
        progression_class = TENANT_PROGRESSION_CLASS_DEGRADED_V1
        stop_reason = lease.block_reason_code or "execution_blocked"
    elif lease is not None and lease.status == LEASE_STATUS_WAITING:
        progression_class = TENANT_PROGRESSION_CLASS_WAITING_UPSTREAM_V1
        stop_reason = "execution_lease_waiting"
    elif run is not None and run.status == PIPELINE_STATUS_RUNNING:
        progression_class = TENANT_PROGRESSION_CLASS_PROGRESSING_V1
        if include_legacy_continuation and continuation_payload and continuation_payload.get(
            "continuation_status"
        ) in (
            CONTINUATION_STATUS_WAITING,
            CONTINUATION_STATUS_STALLED,
        ):
            progression_class = TENANT_PROGRESSION_CLASS_WAITING_UPSTREAM_V1
            stop_reason = str(continuation_payload.get("waiting_on") or "async_wait")
    elif run is not None and run.status == PIPELINE_STATUS_COMPLETED:
        if eligible > 0:
            progression_class = TENANT_PROGRESSION_CLASS_OPERATIONALLY_ALIVE_V1
        elif index_count == 0 and published:
            progression_class = TENANT_PROGRESSION_CLASS_DEGRADED_V1
            stop_reason = "published_epoch_zero_rows"
        else:
            progression_class = TENANT_PROGRESSION_CLASS_IDLE_V1
    elif continuation_payload and continuation_payload.get("recovery_required"):
        progression_class = TENANT_PROGRESSION_CLASS_STALLED_V1
        stop_reason = continuation_payload.get("failure_reason")

    ingest_propagated = bool(
        run is not None
        and phase_status.get(PHASE_07_RETRIEVAL) in (PHASE_STATUS_COMPLETED, PHASE_STATUS_SKIPPED)
    )
    synthesis_propagated = bool(
        run is not None
        and phase_status.get(PHASE_08_SYNTHESIS) in (PHASE_STATUS_COMPLETED, PHASE_STATUS_SKIPPED)
    )

    return {
        "surface_kind": "substrate_operational_progression_status",
        "execution_truth_owner": EXECUTION_OWNER_ID_V1,
        "progression_owner_id": EXECUTION_OWNER_ID_V1,
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(run.id) if run is not None else None,
        "pipeline_status": run.status if run is not None else None,
        "trigger_kind": run.trigger_kind if run is not None else None,
        "progression_class": progression_class,
        "stop_reason": stop_reason,
        "active_phase": first_incomplete_phase_v1(phase_status) if run else None,
        "phase_status": phase_status,
        "continuation": continuation_payload,
        "execution_lease": lease_payload,
        "published_index_epoch": published,
        "retrieval_index_row_count": index_count,
        "synthesis_eligible_scopes": eligible,
        "ingest_propagated_to_retrieval": ingest_propagated,
        "ingest_propagated_to_synthesis": synthesis_propagated,
        "materially_updated_retrieval": index_count > 0,
        "materially_updated_synthesis": eligible > 0,
    }
