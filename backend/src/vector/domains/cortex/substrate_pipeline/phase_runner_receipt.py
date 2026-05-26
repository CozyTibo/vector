"""Phase runner helpers attaching ``SubstratePhaseReceiptV1`` to phase outputs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    complete_phase_v1,
    fail_phase_v1,
    skip_phase_v1,
    wait_phase_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_BLOCKED,
    PHASE_OUTCOME_COMPLETED,
    PHASE_OUTCOME_COMPLETED_EMPTY,
    PHASE_OUTCOME_FAILED,
    PHASE_OUTCOME_SKIPPED_BY_POLICY,
    PHASE_OUTCOME_WAITING_ASYNC,
    build_substrate_phase_receipt_v1,
    merge_receipt_into_output,
)


def _persist_phase_run_for_receipt_outcome_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    out: dict[str, Any],
    outcome: str,
    blocked_reason: str | None = None,
) -> None:
    """Align ``phase_run.status`` with substrate receipt outcome (Wave 1)."""
    receipt = out.get("substrate_phase_receipt")
    effective = str((receipt or {}).get("outcome") or outcome)
    reason = blocked_reason or (receipt or {}).get("blocked_reason") if isinstance(receipt, dict) else blocked_reason
    reason = str(reason)[:500] if reason else None

    if effective == PHASE_OUTCOME_FAILED:
        fail_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=phase_id,
            error=reason or "phase_failed",
            output=out,
        )
        return
    if effective == PHASE_OUTCOME_BLOCKED:
        wait_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=phase_id,
            output=out,
            waiting_reason=reason or "blocked",
        )
        return
    if effective == PHASE_OUTCOME_SKIPPED_BY_POLICY:
        skip_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=phase_id,
            reason=reason or "skipped_by_policy",
            output=out,
        )
        return
    if effective == PHASE_OUTCOME_COMPLETED_EMPTY and phase_id == PHASE_03_IDENTITY:
        wait_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=phase_id,
            output=out,
            waiting_reason=reason or "identity_substrate_no_delta",
        )
        return
    if effective == PHASE_OUTCOME_COMPLETED and reason and phase_id in (
        PHASE_02_CANONICAL,
        PHASE_03_IDENTITY,
    ):
        wait_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=phase_id,
            output=out,
            waiting_reason=reason,
        )
        return
    complete_phase_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=phase_id,
        output=out,
    )


def complete_phase_with_receipt_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    tenant_id: uuid.UUID,
    raw_output: dict[str, Any],
    started_at: str,
    outcome: str = PHASE_OUTCOME_COMPLETED,
    blocked_reason: str | None = None,
    processed_count: int | None = None,
    input_epoch: str | None = None,
) -> dict[str, Any]:
    if outcome == PHASE_OUTCOME_COMPLETED and processed_count is None and not raw_output.get("skipped"):
        from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
            infer_processed_count_v1,
        )

        proc = infer_processed_count_v1(phase_id, raw_output)
        processed_count = proc
        if proc == 0 and phase_id not in (PHASE_03_IDENTITY,) and blocked_reason is None:
            outcome = PHASE_OUTCOME_COMPLETED_EMPTY
    receipt = build_substrate_phase_receipt_v1(
        phase_id=phase_id,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        outcome=outcome,
        raw_output=raw_output,
        started_at=started_at,
        blocked_reason=blocked_reason,
        input_epoch=input_epoch,
        processed_count=processed_count,
    )
    out = merge_receipt_into_output(raw_output, receipt)
    _persist_phase_run_for_receipt_outcome_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=phase_id,
        out=out,
        outcome=outcome,
        blocked_reason=blocked_reason,
    )
    return out


def wait_phase_with_receipt_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    tenant_id: uuid.UUID,
    raw_output: dict[str, Any],
    started_at: str,
    waiting_reason: str,
    blocked_reason: str | None = None,
) -> dict[str, Any]:
    reason = blocked_reason or waiting_reason
    receipt = build_substrate_phase_receipt_v1(
        phase_id=phase_id,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        outcome=PHASE_OUTCOME_BLOCKED,
        raw_output=raw_output,
        started_at=started_at,
        blocked_reason=reason[:500] if reason else None,
    )
    out = merge_receipt_into_output(raw_output, receipt)
    _persist_phase_run_for_receipt_outcome_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=phase_id,
        out=out,
        outcome=PHASE_OUTCOME_BLOCKED,
        blocked_reason=reason,
    )
    return out


def fail_phase_with_receipt_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    tenant_id: uuid.UUID,
    raw_output: dict[str, Any],
    started_at: str,
    error: str,
) -> dict[str, Any]:
    receipt = build_substrate_phase_receipt_v1(
        phase_id=phase_id,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        outcome=PHASE_OUTCOME_FAILED,
        raw_output=raw_output,
        started_at=started_at,
        blocked_reason=error[:500],
    )
    out = merge_receipt_into_output(raw_output, receipt)
    fail_phase_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=phase_id,
        error=error,
        output=out,
    )
    return out


def skip_phase_with_receipt_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    tenant_id: uuid.UUID,
    reason: str,
    started_at: str,
    raw_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw = dict(raw_output or {})
    raw.setdefault("skipped", True)
    raw["reason"] = reason
    receipt = build_substrate_phase_receipt_v1(
        phase_id=phase_id,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        outcome=PHASE_OUTCOME_SKIPPED_BY_POLICY,
        raw_output=raw,
        started_at=started_at,
        blocked_reason=reason[:500],
        processed_count=0,
    )
    out = merge_receipt_into_output(raw, receipt)
    skip_phase_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=phase_id,
        reason=reason,
        output=out,
    )
    return out


def complete_async_phase_with_receipt_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    tenant_id: uuid.UUID,
    raw_output: dict[str, Any],
    started_at: str,
) -> dict[str, Any]:
    return complete_phase_with_receipt_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=phase_id,
        tenant_id=tenant_id,
        raw_output=raw_output,
        started_at=started_at,
        outcome=PHASE_OUTCOME_WAITING_ASYNC,
        processed_count=1 if raw_output.get("job_id") else 0,
    )
