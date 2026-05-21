"""Phase 08.5 P085-16 — stalled traversal recovery (**G-P085-WALK-03**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-traversal-completion-doctrine.md`` §Recovery.
"""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_retry import (
    CESP_WALK_RETRY_DETAIL_KEY_V1,
    GP085_WALK02_GATE_ID_V1,
    get_traversal_retry_max_attempts_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    GP085_WALK01_GATE_ID_V1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_05_TRAVERSAL
from vector.domains.cortex.substrate_pipeline.pipeline_dead_letter import (
    FAILURE_CLASS_WALK_POISON,
    record_pipeline_dead_letter_v1,
)
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import (
    CortexOctsDurableWalkRecord,
)
from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1
from vector.domains.cortex.traversal.walk_api_contract import WalkApiRecordV1

PHASE085_STALLED_TRAVERSAL_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_STALLED_TRAVERSAL_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-traversal-completion-doctrine.md"
)

GP085_WALK03_GATE_ID_V1: Final[str] = "G-P085-WALK-03"

CELERY_STALLED_TRAVERSAL_RECOVERY_TASK_NAME_V1: Final[str] = (
    "vector.cortex.operational_runtime.stalled_traversal_recovery_pass"
)

CESP_WALK_STALL_DETAIL_KEY_V1: Final[str] = "cesp_walk_stall_v1"

POISON_REASON_MAX_RECOVERY_PASSES_V1: Final[str] = "max_stall_recovery_passes"
POISON_REASON_RETRY_BUDGET_EXHAUSTED_V1: Final[str] = "retry_budget_exhausted"

RECOVERY_ACTION_REENQUEUE_V1: Final[str] = "re_enqueue_pending_walk"
RECOVERY_ACTION_CANCEL_POISON_DLQ_V1: Final[str] = "cancel_poison_walk_to_dlq"

_PENDING_STATUSES_V1: Final[frozenset[str]] = frozenset({"queued", "running"})


class SubstrateStalledTraversalRecoveryError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_traversal_stall_threshold_seconds_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(60, int(get_settings().cortex_traversal_stall_seconds))
    except Exception:  # noqa: BLE001
        return 1800


def get_traversal_stall_recovery_pass_limit_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_traversal_stall_recovery_pass_limit))
    except Exception:  # noqa: BLE001
        return 32


def get_traversal_poison_max_recovery_passes_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_traversal_poison_max_recovery_passes))
    except Exception:  # noqa: BLE001
        return 5


def _stall_detail_from_request_v1(request_body: dict[str, Any]) -> dict[str, Any]:
    raw = request_body.get(CESP_WALK_STALL_DETAIL_KEY_V1)
    return dict(raw) if isinstance(raw, dict) else {}


def _merge_stall_detail_v1(
    request_body: dict[str, Any],
    *,
    patch: dict[str, Any],
) -> dict[str, Any]:
    body = dict(request_body)
    detail = _stall_detail_from_request_v1(body)
    detail.update(patch)
    body[CESP_WALK_STALL_DETAIL_KEY_V1] = detail
    return body


def _parse_iso_datetime_v1(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def seconds_since_last_completed_walk_v1(
    *,
    last_walk_completed_at: str | None,
    now: datetime | None = None,
) -> float | None:
    """Elapsed seconds since last completed walk; ``None`` when no completion yet."""
    completed = _parse_iso_datetime_v1(last_walk_completed_at)
    if completed is None:
        return None
    ref = now or datetime.now(tz=UTC)
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=UTC)
    return max(0.0, (ref - completed).total_seconds())


def detect_stalled_traversal_v1(
    *,
    pending_walks: int,
    last_walk_completed_at: str | None,
    stall_threshold_seconds: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Detect stall: ``pending_walks > 0`` and idle since last completion exceeds ``T_stall``."""
    t_stall = (
        int(stall_threshold_seconds)
        if stall_threshold_seconds is not None
        else get_traversal_stall_threshold_seconds_v1()
    )
    pending = int(pending_walks)
    elapsed = seconds_since_last_completed_walk_v1(
        last_walk_completed_at=last_walk_completed_at,
        now=now,
    )
    if pending <= 0:
        return {
            "stalled": False,
            "reason": "no_pending_walks",
            "pending_walks": pending,
            "stall_threshold_seconds": t_stall,
            "seconds_since_last_completion": elapsed,
        }
    if elapsed is None:
        stalled = True
        reason = "pending_without_completed_walk"
    elif elapsed > t_stall:
        stalled = True
        reason = "last_completion_exceeds_t_stall"
    else:
        stalled = False
        reason = "within_stall_threshold"
    return {
        "stalled": stalled,
        "reason": reason,
        "pending_walks": pending,
        "stall_threshold_seconds": t_stall,
        "seconds_since_last_completion": elapsed,
        "last_walk_completed_at": last_walk_completed_at,
    }


def classify_walk_poison_v1(record: WalkApiRecordV1) -> tuple[bool, str]:
    """Poison walks are cancelled to DLQ instead of re-enqueued."""
    if record.status not in _PENDING_STATUSES_V1:
        return False, ""

    body = dict(record.request_body or {})
    stall_detail = _stall_detail_from_request_v1(body)
    recovery_passes = int(stall_detail.get("recovery_pass_count") or 0)
    if recovery_passes >= get_traversal_poison_max_recovery_passes_v1():
        return True, POISON_REASON_MAX_RECOVERY_PASSES_V1

    retry_detail = body.get(CESP_WALK_RETRY_DETAIL_KEY_V1)
    if isinstance(retry_detail, dict):
        retry_attempts = int(retry_detail.get("retry_attempt_count") or 0)
        if retry_attempts > get_traversal_retry_max_attempts_v1():
            return True, POISON_REASON_RETRY_BUDGET_EXHAUSTED_V1

    return False, ""


def _resolve_pipeline_run_id_for_walk_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    request_body: dict[str, Any],
) -> uuid.UUID | None:
    raw = request_body.get("substrate_pipeline_run_id")
    if raw:
        try:
            return uuid.UUID(str(raw))
        except ValueError:
            pass
    from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1

    running = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    return running.id if running is not None else None


def cancel_poison_walk_to_dlq_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    record: WalkApiRecordV1,
    poison_reason: str,
) -> dict[str, Any]:
    """Cancel poison walk and record durable DLQ when pipeline scope is known."""
    store = resolve_octs_walk_store_v1(session)
    body = _merge_stall_detail_v1(
        dict(record.request_body or {}),
        patch={
            "poison": True,
            "poison_reason": poison_reason,
            "poison_at": datetime.now(tz=UTC).isoformat(),
        },
    )
    row = session.get(CortexOctsDurableWalkRecord, record.walk_id)
    if row is not None and row.tenant_id == tenant_id:
        row.request_body = body
        session.flush()

    cancelled = store.cancel(tenant_id, record.walk_id)
    dlq_row_id: str | None = None
    pipeline_run_id = _resolve_pipeline_run_id_for_walk_v1(
        session,
        tenant_id=tenant_id,
        request_body=body,
    )
    if pipeline_run_id is not None:
        dlq = record_pipeline_dead_letter_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_05_TRAVERSAL,
            failure_class=FAILURE_CLASS_WALK_POISON,
            async_job_id=record.walk_id,
            failure_detail=poison_reason,
            detail={
                "walk_id": str(record.walk_id),
                "gate_id": GP085_WALK03_GATE_ID_V1,
                "poison_reason": poison_reason,
            },
        )
        dlq_row_id = str(dlq.id)

    return {
        "action": RECOVERY_ACTION_CANCEL_POISON_DLQ_V1,
        "walk_id": str(record.walk_id),
        "poison_reason": poison_reason,
        "cancelled": cancelled is not None and cancelled.status == "cancelled",
        "dead_letter_id": dlq_row_id,
        "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else None,
    }


def re_enqueue_pending_walk_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    record: WalkApiRecordV1,
) -> dict[str, Any]:
    """Re-enqueue one pending walk (deterministic job id rotation)."""
    store = resolve_octs_walk_store_v1(session)
    body = dict(record.request_body or {})
    stall_detail = _stall_detail_from_request_v1(body)
    attempt = int(stall_detail.get("recovery_pass_count") or 0) + 1
    merged_body = _merge_stall_detail_v1(
        body,
        patch={
            "recovery_pass_count": attempt,
            "last_re_enqueued_at": datetime.now(tz=UTC).isoformat(),
        },
    )
    row = session.get(CortexOctsDurableWalkRecord, record.walk_id)
    if row is not None and row.tenant_id == tenant_id:
        row.request_body = merged_body
        session.flush()

    new_job_id = str(uuid.uuid4())
    requeued = store.requeue_pending_walk_v1(
        tenant_id,
        record.walk_id,
        job_id=new_job_id,
    )
    return {
        "action": RECOVERY_ACTION_REENQUEUE_V1,
        "walk_id": str(record.walk_id),
        "recovery_pass_count": attempt,
        "job_id": new_job_id,
        "requeued": requeued is not None and requeued.status == "queued",
    }


def evaluate_tenant_traversal_stall_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Tenant walk queue health + stall detection."""
    store = resolve_octs_walk_store_v1(session)
    snapshot = store.get_tenant_walk_queue_snapshot_v1(tenant_id)
    detection = detect_stalled_traversal_v1(
        pending_walks=int(snapshot["pending_count"]),
        last_walk_completed_at=snapshot.get("last_walk_completed_at"),
    )
    return {
        "gate_id": GP085_WALK03_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "pending_walks": int(snapshot["pending_count"]),
        "last_walk_completed_at": snapshot.get("last_walk_completed_at"),
        **detection,
    }


def apply_stalled_walk_recovery_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    record: WalkApiRecordV1,
) -> dict[str, Any]:
    """Re-enqueue or poison-cancel one pending walk."""
    if record.status not in _PENDING_STATUSES_V1:
        return {"skipped": True, "reason": "not_pending", "walk_id": str(record.walk_id)}

    is_poison, poison_reason = classify_walk_poison_v1(record)
    if is_poison:
        return cancel_poison_walk_to_dlq_v1(
            session,
            tenant_id=tenant_id,
            record=record,
            poison_reason=poison_reason,
        )
    return re_enqueue_pending_walk_v1(session, tenant_id=tenant_id, record=record)


def run_stalled_traversal_recovery_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run **G-P085-WALK-03** when tenant traversal queue is stalled."""
    eval_out = evaluate_tenant_traversal_stall_v1(session, tenant_id=tenant_id)
    if not eval_out.get("stalled"):
        return {
            "gate_id": GP085_WALK03_GATE_ID_V1,
            "related_gate_ids": [GP085_WALK01_GATE_ID_V1, GP085_WALK02_GATE_ID_V1],
            "tenant_id": str(tenant_id),
            "recovered": False,
            "evaluation": eval_out,
            "outcomes": [],
        }

    lim = limit if limit is not None else get_traversal_stall_recovery_pass_limit_v1()
    store = resolve_octs_walk_store_v1(session)
    snapshot = store.get_tenant_walk_queue_snapshot_v1(tenant_id)
    pending = list(snapshot.get("pending_records") or [])[:lim]
    outcomes = [
        apply_stalled_walk_recovery_v1(session, tenant_id=tenant_id, record=rec)
        for rec in pending
    ]

    by_action: dict[str, int] = {}
    for o in outcomes:
        act = str(o.get("action") or o.get("reason") or "skipped")
        by_action[act] = by_action.get(act, 0) + 1

    return {
        "gate_id": GP085_WALK03_GATE_ID_V1,
        "related_gate_ids": [GP085_WALK01_GATE_ID_V1, GP085_WALK02_GATE_ID_V1],
        "tenant_id": str(tenant_id),
        "recovered": True,
        "evaluation": eval_out,
        "pending_processed": len(pending),
        "outcomes": outcomes,
        "outcome_counts": by_action,
        "stall_threshold_seconds": get_traversal_stall_threshold_seconds_v1(),
        "poison_max_recovery_passes": get_traversal_poison_max_recovery_passes_v1(),
    }


def schedule_stalled_traversal_recovery_pass_v1(
    *,
    tenant_id: uuid.UUID,
    countdown: int | None = None,
    session: Session | None = None,
) -> dict[str, Any]:
    """M9: synchronous inline pass only (admin; not execution slice)."""
    _ = countdown

    if session is not None:
        pass_out = run_stalled_traversal_recovery_pass_v1(session, tenant_id=tenant_id)
        return {"scheduled": True, "path": "inline_execution_slice", "pass": pass_out}
    from vector.infrastructure.db.session import session_scope

    with session_scope() as scoped:
        pass_out = run_stalled_traversal_recovery_pass_v1(scoped, tenant_id=tenant_id)
        scoped.commit()
        return {"scheduled": True, "path": "inline_execution_slice", "pass": pass_out}


def build_substrate_stalled_traversal_recovery_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_stalled_traversal_runtime_schema_version": int(
            PHASE085_STALLED_TRAVERSAL_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_STALLED_TRAVERSAL_SPEC_REF_V1,
        "primary_gate_id": GP085_WALK03_GATE_ID_V1,
        "detection_rule": "pending_walks > 0 AND seconds_since_last_completion > T_stall",
        "recovery_actions": [
            RECOVERY_ACTION_REENQUEUE_V1,
            RECOVERY_ACTION_CANCEL_POISON_DLQ_V1,
        ],
        "failure_class_walk_poison": FAILURE_CLASS_WALK_POISON,
        "stall_threshold_seconds": get_traversal_stall_threshold_seconds_v1(),
        "poison_max_recovery_passes": get_traversal_poison_max_recovery_passes_v1(),
        "celery_task_name": CELERY_STALLED_TRAVERSAL_RECOVERY_TASK_NAME_V1,
        "pass_entrypoint": "run_stalled_traversal_recovery_pass_v1",
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_stalled_traversal_recovery"
        ),
    }


def verify_gp085_walk03_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_stalled_traversal_recovery_catalog_v1()
    if cat["primary_gate_id"] != GP085_WALK03_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    det = detect_stalled_traversal_v1(
        pending_walks=2,
        last_walk_completed_at="2000-01-01T00:00:00+00:00",
        stall_threshold_seconds=60,
    )
    if not det.get("stalled"):
        errors.append("stalled_detection_should_fire")
    det_ok = detect_stalled_traversal_v1(
        pending_walks=0,
        last_walk_completed_at="2000-01-01T00:00:00+00:00",
        stall_threshold_seconds=60,
    )
    if det_ok.get("stalled"):
        errors.append("no_pending_should_not_stall")

    src = inspect.getsource(detect_stalled_traversal_v1)
    if "random" in src.lower():
        errors.append("probabilistic_stall_detection_forbidden")

    from vector.domains.cortex.substrate_pipeline import pipeline_dead_letter as dlq

    if FAILURE_CLASS_WALK_POISON not in dlq.FAILURE_CLASS_IDS_V1:
        errors.append("walk_poison_failure_class_missing")

    import importlib.util

    if importlib.util.find_spec("app.tasks.cortex_substrate_stalled_traversal_recovery") is not None:
        errors.append("celery_stalled_traversal_module_must_be_deleted_m9")

    passed = not errors
    return {
        "id": GP085_WALK03_GATE_ID_V1,
        "name": "cesp_substrate_stalled_traversal_recovery",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
