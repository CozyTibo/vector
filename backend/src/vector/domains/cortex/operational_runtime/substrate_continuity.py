"""Phase 08.5 P085-05 — substrate continuation state machine (**G-P085-CONT-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-substrate-continuity-doctrine.md``.
Runtime persistence: ``vector.domains.cortex.substrate_pipeline.pipeline_continuation``.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_CONTINUATION_NONCE_FIELD_V1,
    PHASE085_NORMATIVE_TREE_V1,
    PHASE085_RESUME_RECEIPT_HASH_FIELD_V1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_COMPLETED,
    CONTINUATION_STATUS_FAILED,
    CONTINUATION_STATUS_RECOVERING,
    CONTINUATION_STATUS_RESUMED,
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    DEFAULT_STALL_THRESHOLD_SECONDS,
    WAITING_ON_TCRE_COMPLETION,
    compute_continuation_nonce_v1,
    compute_resume_identity_digest_v1,
    compute_resume_receipt_hash_v1,
)

PHASE085_SUBSTRATE_CONTINUITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_SUBSTRATE_CONTINUITY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-substrate-continuity-doctrine.md"
)

GP085_CONT01_GATE_ID_V1: Final[str] = "G-P085-CONT-01"

# Ephemeral create hop (not always persisted) → first durable row is WAITING.
CONTINUATION_STATUS_CREATED: Final[str] = "CREATED"

CONTINUATION_STATUS_IDS_V1: Final[tuple[str, ...]] = (
    CONTINUATION_STATUS_CREATED,
    CONTINUATION_STATUS_WAITING,
    CONTINUATION_STATUS_RESUMED,
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_RECOVERING,
    CONTINUATION_STATUS_COMPLETED,
    CONTINUATION_STATUS_FAILED,
)

WAITING_ON_KINDS_V1: Final[tuple[str, ...]] = (
    WAITING_ON_TCRE_COMPLETION,
    "TRAVERSAL_COMPLETION",
    "INDEX_PUBLISH",
)

_TERMINAL_CONTINUATION_STATUSES_V1: Final[frozenset[str]] = frozenset(
    {CONTINUATION_STATUS_COMPLETED, CONTINUATION_STATUS_FAILED}
)

_CONTINUATION_TRANSITIONS_V1: Final[dict[str, frozenset[str]]] = {
    CONTINUATION_STATUS_WAITING: frozenset(
        {
            CONTINUATION_STATUS_RESUMED,
            CONTINUATION_STATUS_STALLED,
            CONTINUATION_STATUS_FAILED,
            CONTINUATION_STATUS_COMPLETED,
        }
    ),
    CONTINUATION_STATUS_RESUMED: frozenset(
        {CONTINUATION_STATUS_COMPLETED, CONTINUATION_STATUS_FAILED}
    ),
    CONTINUATION_STATUS_STALLED: frozenset(
        {
            CONTINUATION_STATUS_RECOVERING,
            CONTINUATION_STATUS_WAITING,
            CONTINUATION_STATUS_FAILED,
        }
    ),
    CONTINUATION_STATUS_RECOVERING: frozenset(
        {
            CONTINUATION_STATUS_RESUMED,
            CONTINUATION_STATUS_WAITING,
            CONTINUATION_STATUS_COMPLETED,
            CONTINUATION_STATUS_FAILED,
        }
    ),
}

_CONTINUATION_METRICS_V1: dict[str, int] = defaultdict(int)

_CONTINUATION_METRIC_NAMES_V1: Final[tuple[str, ...]] = (
    "substrate_continuation_waiting_gauge",
    "substrate_continuation_stall_total",
    "substrate_resume_duplicate_total",
    "substrate_phase_07_enqueue_total",
)


class SubstrateContinuationError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_continuation_stall_threshold_seconds_v1() -> int:
    from vector.settings import get_settings

    return int(get_settings().cortex_substrate_continuation_stall_seconds)


def increment_continuation_metric_v1(metric_name: str, *, delta: int = 1) -> None:
    if metric_name in _CONTINUATION_METRIC_NAMES_V1:
        _CONTINUATION_METRICS_V1[metric_name] += max(1, int(delta))


def snapshot_continuation_metrics_v1() -> dict[str, int]:
    return {name: int(_CONTINUATION_METRICS_V1.get(name, 0)) for name in _CONTINUATION_METRIC_NAMES_V1}


def validate_continuation_status_transition_v1(
    *,
    from_status: str | None,
    to_status: str,
) -> None:
    """Raise when ``to_status`` is not legal from ``from_status``."""
    if to_status not in CONTINUATION_STATUS_IDS_V1:
        raise SubstrateContinuationError(
            "unknown_continuation_status",
            detail={"to_status": to_status},
        )
    if from_status is None:
        if to_status not in (CONTINUATION_STATUS_CREATED, CONTINUATION_STATUS_WAITING):
            raise SubstrateContinuationError(
                "invalid_initial_continuation_status",
                detail={"to_status": to_status},
            )
        return
    if from_status in _TERMINAL_CONTINUATION_STATUSES_V1:
        raise SubstrateContinuationError(
            "terminal_continuation_status",
            detail={"from_status": from_status, "to_status": to_status},
        )
    allowed = _CONTINUATION_TRANSITIONS_V1.get(from_status, frozenset())
    if to_status not in allowed and to_status != from_status:
        raise SubstrateContinuationError(
            "illegal_continuation_transition",
            detail={"from_status": from_status, "to_status": to_status, "allowed": sorted(allowed)},
        )


def assert_waiting_on_kind_v1(waiting_on: str | None) -> None:
    if waiting_on is not None and waiting_on not in WAITING_ON_KINDS_V1:
        raise SubstrateContinuationError(
            "unknown_waiting_on_kind",
            detail={"waiting_on": waiting_on, "allowed": list(WAITING_ON_KINDS_V1)},
        )


def assert_continuation_row_contract_v1(row: Mapping[str, Any]) -> None:
    """Required durable fields per doctrine §Durable model."""
    required = (
        "tenant_id",
        "substrate_pipeline_run_id",
        "current_phase",
        "continuation_status",
        "continuation_nonce",
        "retry_count",
        "recovery_required",
    )
    missing = [k for k in required if row.get(k) is None]
    if missing:
        raise SubstrateContinuationError(
            "continuation_row_missing_fields",
            detail={"missing": missing},
        )
    assert_waiting_on_kind_v1(
        str(row["waiting_on"]) if row.get("waiting_on") is not None else None
    )
    validate_continuation_status_transition_v1(
        from_status=None,
        to_status=str(row["continuation_status"]),
    )


def continuation_row_to_public_dict_v1(row: Any) -> dict[str, Any]:
    """Serialize ORM row for admin continuation inspector."""
    return {
        "continuation_status": row.continuation_status,
        "current_phase": row.current_phase,
        "waiting_on": row.waiting_on,
        "async_job_id": str(row.async_job_id) if row.async_job_id else None,
        "async_job_type": row.async_job_type,
        "continuation_nonce": row.continuation_nonce,
        PHASE085_RESUME_RECEIPT_HASH_FIELD_V1: row.resume_receipt_hash,
        "resume_identity_digest": row.resume_identity_digest,
        "retry_count": int(row.retry_count or 0),
        "recovery_required": bool(row.recovery_required),
        "failure_reason": row.failure_reason,
        "last_heartbeat_at": row.last_heartbeat_at.isoformat() if row.last_heartbeat_at else None,
        "resumed_at": row.resumed_at.isoformat() if row.resumed_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "detail_json": dict(row.detail_json or {}),
        "recovery_receipts": list((row.detail_json or {}).get("recovery_receipts") or []),
    }


def build_substrate_continuity_catalog_v1() -> dict[str, Any]:
    """Doctrine catalog for continuation state machine (P085-05)."""
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_substrate_continuity_runtime_schema_version": int(
            PHASE085_SUBSTRATE_CONTINUITY_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_SUBSTRATE_CONTINUITY_SPEC_REF_V1,
        "primary_gate_id": GP085_CONT01_GATE_ID_V1,
        "continuation_status_ids": list(CONTINUATION_STATUS_IDS_V1),
        "waiting_on_kinds": list(WAITING_ON_KINDS_V1),
        "terminal_statuses": sorted(_TERMINAL_CONTINUATION_STATUSES_V1),
        "allowed_transitions": {
            k: sorted(v) for k, v in sorted(_CONTINUATION_TRANSITIONS_V1.items())
        },
        "state_machine_diagram": (
            "CREATED → WAITING → RESUMED → COMPLETED; "
            "WAITING → STALLED → RECOVERING → RESUMED"
        ),
        "stall_threshold_seconds_default": int(DEFAULT_STALL_THRESHOLD_SECONDS),
        "stall_threshold_seconds_configured": get_continuation_stall_threshold_seconds_v1(),
        "continuation_nonce_field": PHASE085_CONTINUATION_NONCE_FIELD_V1,
        "resume_receipt_hash_field": PHASE085_RESUME_RECEIPT_HASH_FIELD_V1,
        "durable_table": "cortex_pipeline_continuation_states",
        "runtime_package": "vector.domains.cortex.substrate_pipeline.pipeline_continuation",
        "operational_metrics": list(_CONTINUATION_METRIC_NAMES_V1),
        "resume_digest_functions": [
            "compute_continuation_nonce_v1",
            "compute_resume_identity_digest_v1",
            "compute_resume_receipt_hash_v1",
        ],
    }


def assert_phase06_must_persist_waiting_v1(
    *,
    continuation_present: bool,
    waiting_on: str | None = None,
) -> None:
    """Phase 06 MUST NOT return without durable WAITING / TCRE_COMPLETION."""
    if not continuation_present:
        raise SubstrateContinuationError(
            "phase06_missing_continuation_wait",
            detail={"required_waiting_on": WAITING_ON_TCRE_COMPLETION},
        )
    if waiting_on is not None and waiting_on != WAITING_ON_TCRE_COMPLETION:
        raise SubstrateContinuationError(
            "phase06_wrong_waiting_on",
            detail={"waiting_on": waiting_on},
        )


def verify_gp085_cont01_state_machine_static() -> dict[str, Any]:
    errors: list[str] = []
    for from_status, targets in _CONTINUATION_TRANSITIONS_V1.items():
        for to_status in targets:
            try:
                validate_continuation_status_transition_v1(
                    from_status=from_status,
                    to_status=to_status,
                )
            except SubstrateContinuationError as exc:
                errors.append(f"transition_table_invalid:{from_status}->{to_status}:{exc.code}")

    try:
        validate_continuation_status_transition_v1(
            from_status=CONTINUATION_STATUS_COMPLETED,
            to_status=CONTINUATION_STATUS_WAITING,
        )
    except SubstrateContinuationError:
        pass
    else:
        errors.append("completed_to_waiting_should_fail")

    try:
        assert_continuation_row_contract_v1(
            {
                "tenant_id": "t",
                "substrate_pipeline_run_id": "p",
                "current_phase": "phase_06_tcre",
                "continuation_status": CONTINUATION_STATUS_WAITING,
                "continuation_nonce": "n",
                "waiting_on": WAITING_ON_TCRE_COMPLETION,
                "retry_count": 0,
                "recovery_required": False,
            },
        )
    except SubstrateContinuationError as exc:
        errors.append(f"row_contract_rejected_valid_row:{exc.code}")

    nonce = compute_continuation_nonce_v1(
        tenant_id=uuid.uuid4(),
        pipeline_run_id=uuid.uuid4(),
        waiting_on=WAITING_ON_TCRE_COMPLETION,
    )
    if len(nonce) < 16:
        errors.append("continuation_nonce_too_short")

    passed = not errors
    return {
        "id": GP085_CONT01_GATE_ID_V1,
        "name": "cesp_continuation_state_machine",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
