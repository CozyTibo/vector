"""Phase 08.5 P085-08 — replay-safe recovery receipts (**G-P085-REC-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-recovery-continuity-doctrine.md`` §Recovery receipts.
Persistence: ``continuation.detail_json.recovery_receipts[]`` via ``append_recovery_receipt_v1``.
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_CONTINUATION_NONCE_FIELD_V1,
    PHASE085_NORMATIVE_TREE_V1,
    PHASE085_RESUME_RECEIPT_HASH_FIELD_V1,
)
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.infrastructure.db.models.cortex_pipeline_continuation import (
    CortexPipelineContinuationState,
)

PHASE085_RECOVERY_RECEIPT_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_RECOVERY_RECEIPT_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-recovery-continuity-doctrine.md"
)

GP085_REC01_GATE_ID_V1: Final[str] = "G-P085-REC-01"

RECOVERY_RECEIPT_DIGEST_FIELD_V1: Final[str] = "recovery_receipt_digest"

RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07: Final[str] = "resume_phase_07"
RECOVERY_RECEIPT_ACTION_REBIND_TCRE: Final[str] = "rebind_tcre"
RECOVERY_RECEIPT_ACTION_REPLAY_PHASE_06: Final[str] = "replay_phase_06"
RECOVERY_RECEIPT_ACTION_REPLAY_CALLBACK: Final[str] = "replay_callback"
RECOVERY_RECEIPT_ACTION_RETRY_CONTINUATION: Final[str] = "retry_continuation"
RECOVERY_RECEIPT_ACTION_MARK_UNRECOVERABLE: Final[str] = "mark_unrecoverable"

RECOVERY_RECEIPT_ACTION_IDS_V1: Final[tuple[str, ...]] = (
    RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07,
    RECOVERY_RECEIPT_ACTION_REBIND_TCRE,
    RECOVERY_RECEIPT_ACTION_REPLAY_PHASE_06,
    RECOVERY_RECEIPT_ACTION_REPLAY_CALLBACK,
    RECOVERY_RECEIPT_ACTION_RETRY_CONTINUATION,
    RECOVERY_RECEIPT_ACTION_MARK_UNRECOVERABLE,
)

RECOVERY_RECEIPT_OUTCOME_RECOVERED: Final[str] = "recovered"
RECOVERY_RECEIPT_OUTCOME_SKIPPED: Final[str] = "skipped"
RECOVERY_RECEIPT_OUTCOME_FAILED: Final[str] = "failed"

RECOVERY_RECEIPT_OUTCOME_IDS_V1: Final[tuple[str, ...]] = (
    RECOVERY_RECEIPT_OUTCOME_RECOVERED,
    RECOVERY_RECEIPT_OUTCOME_SKIPPED,
    RECOVERY_RECEIPT_OUTCOME_FAILED,
)

RECOVERY_RECEIPT_REQUIRED_FIELDS_V1: Final[tuple[str, ...]] = (
    RECOVERY_RECEIPT_DIGEST_FIELD_V1,
    "action",
    PHASE085_CONTINUATION_NONCE_FIELD_V1,
    "prior_resume_receipt_hash",
    "outcome",
)

MAX_RECOVERY_RECEIPTS_PER_CONTINUATION_V1: Final[int] = 20

_RECOVERY_RECEIPT_METRICS_V1: dict[str, int] = {
    "substrate_recovery_receipt_persisted_total": 0,
}


class RecoveryReceiptError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def increment_recovery_receipt_metric_v1(metric_name: str, *, delta: int = 1) -> None:
    if metric_name in _RECOVERY_RECEIPT_METRICS_V1:
        _RECOVERY_RECEIPT_METRICS_V1[metric_name] += max(1, int(delta))


def snapshot_recovery_receipt_metrics_v1() -> dict[str, int]:
    return dict(_RECOVERY_RECEIPT_METRICS_V1)


def assert_recovery_receipt_action_v1(action: str) -> None:
    if action not in RECOVERY_RECEIPT_ACTION_IDS_V1:
        raise RecoveryReceiptError(
            "recovery_action_not_closed",
            detail={"action": action, "allowed": list(RECOVERY_RECEIPT_ACTION_IDS_V1)},
        )


def assert_recovery_receipt_outcome_v1(outcome: str) -> None:
    if outcome not in RECOVERY_RECEIPT_OUTCOME_IDS_V1:
        raise RecoveryReceiptError(
            "recovery_outcome_not_closed",
            detail={"outcome": outcome, "allowed": list(RECOVERY_RECEIPT_OUTCOME_IDS_V1)},
        )


def compute_recovery_receipt_digest_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    action: str,
    continuation_nonce: str,
    prior_resume_receipt_hash: str | None,
    outcome: str,
) -> str:
    """Canonical digest for one recovery attempt (**G-P085-REC-01**)."""
    assert_recovery_receipt_action_v1(action)
    assert_recovery_receipt_outcome_v1(outcome)
    return hash_reasoning_canonical_json_sha256_v1(
        {
            "tenant_id": str(tenant_id),
            "pipeline_run_id": str(pipeline_run_id),
            "action": action,
            "continuation_nonce": continuation_nonce,
            "prior_resume_receipt_hash": prior_resume_receipt_hash,
            "outcome": outcome,
            "purpose": "substrate_recovery_receipt_digest_v1",
        }
    )


def assert_recovery_receipt_contract_v1(receipt: Mapping[str, Any]) -> None:
    """Validate persisted recovery receipt shape."""
    missing = [k for k in RECOVERY_RECEIPT_REQUIRED_FIELDS_V1 if k not in receipt]
    if missing:
        raise RecoveryReceiptError(
            "recovery_receipt_missing_fields",
            detail={"missing": missing},
        )
    assert_recovery_receipt_action_v1(str(receipt["action"]))
    assert_recovery_receipt_outcome_v1(str(receipt["outcome"]))
    digest = str(receipt[RECOVERY_RECEIPT_DIGEST_FIELD_V1])
    if len(digest.replace("sha256:", "")) < 64:
        raise RecoveryReceiptError(
            "recovery_receipt_digest_too_short",
            detail={RECOVERY_RECEIPT_DIGEST_FIELD_V1: digest},
        )


def build_recovery_receipt_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    action: str,
    continuation_nonce: str,
    outcome: str,
    prior_resume_receipt_hash: str | None = None,
    recorded_at: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one recovery receipt dict before persistence."""
    digest_hex = compute_recovery_receipt_digest_v1(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        action=action,
        continuation_nonce=continuation_nonce,
        prior_resume_receipt_hash=prior_resume_receipt_hash,
        outcome=outcome,
    )
    body: dict[str, Any] = {
        "schema_version": PHASE085_RECOVERY_RECEIPT_RUNTIME_SCHEMA_VERSION,
        RECOVERY_RECEIPT_DIGEST_FIELD_V1: f"sha256:{digest_hex}",
        "action": action,
        PHASE085_CONTINUATION_NONCE_FIELD_V1: continuation_nonce,
        "prior_resume_receipt_hash": prior_resume_receipt_hash,
        "outcome": outcome,
        "recorded_at": recorded_at or datetime.now(UTC).isoformat(),
    }
    if extra:
        body.update(dict(extra))
    assert_recovery_receipt_contract_v1(body)
    return body


def list_recovery_receipts_v1(continuation: CortexPipelineContinuationState) -> list[dict[str, Any]]:
    detail = dict(continuation.detail_json or {})
    rows = list(detail.get("recovery_receipts") or [])
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, Mapping):
            out.append(dict(row))
    return out


def list_recovery_receipts_for_pipeline_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> list[dict[str, Any]]:
    from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
        get_continuation_for_pipeline_v1,
    )

    cont = get_continuation_for_pipeline_v1(session, pipeline_run_id=pipeline_run_id)
    if cont is None:
        return []
    return list_recovery_receipts_v1(cont)


def persist_recovery_receipt_v1(
    session: Session,
    *,
    continuation: CortexPipelineContinuationState,
    action: str,
    outcome: str,
    prior_resume_receipt_hash: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Append replay-safe recovery receipt to continuation detail (**G-P085-REC-01**)."""
    from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
        append_recovery_receipt_v1,
    )

    prior = prior_resume_receipt_hash
    if prior is None:
        prior = continuation.resume_receipt_hash

    receipt = build_recovery_receipt_v1(
        tenant_id=continuation.tenant_id,
        pipeline_run_id=continuation.substrate_pipeline_run_id,
        action=action,
        continuation_nonce=continuation.continuation_nonce,
        outcome=outcome,
        prior_resume_receipt_hash=prior,
        extra=extra,
    )
    append_recovery_receipt_v1(continuation, receipt=receipt)
    session.flush()
    increment_recovery_receipt_metric_v1("substrate_recovery_receipt_persisted_total")
    return receipt


def normalize_stalled_recovery_action_v1(
    action: str,
    *,
    reason: str | None = None,
    recommendation: str | None = None,
) -> str:
    """Map stalled-recovery operator/auto action to closed receipt action id."""
    if action in RECOVERY_RECEIPT_ACTION_IDS_V1:
        return action
    if action == "rebind_tcre":
        return RECOVERY_RECEIPT_ACTION_REBIND_TCRE
    if action == "replay_callback":
        return RECOVERY_RECEIPT_ACTION_REPLAY_CALLBACK
    if action == "replay_phase_06":
        return RECOVERY_RECEIPT_ACTION_REPLAY_PHASE_06
    if action == "resume_phase_07":
        return RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07
    if action == "mark_unrecoverable":
        return RECOVERY_RECEIPT_ACTION_MARK_UNRECOVERABLE
    reason_key = (reason or "").strip()
    if reason_key == "phase_07_already_complete":
        return RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07
    if reason_key == "phase_06_re_enqueued":
        return RECOVERY_RECEIPT_ACTION_REPLAY_PHASE_06
    if reason_key == "phase_07_force_enqueued":
        return RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07
    if reason_key.startswith("duplicate_resume"):
        return RECOVERY_RECEIPT_ACTION_REPLAY_CALLBACK
    if reason_key.startswith("phase_07_already"):
        return RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07
    if "tcre" in reason_key and "failed" in reason_key:
        return RECOVERY_RECEIPT_ACTION_REPLAY_PHASE_06
    if recommendation == "rebind_tcre_job":
        return RECOVERY_RECEIPT_ACTION_REBIND_TCRE
    if recommendation == "resume_phase_07":
        return RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07
    if recommendation and "replay_phase_06" in recommendation:
        return RECOVERY_RECEIPT_ACTION_REPLAY_PHASE_06
    if reason_key in ("dlq_auto_retry_budget_exhausted", "continuation_not_found"):
        return RECOVERY_RECEIPT_ACTION_RETRY_CONTINUATION
    if action == "auto":
        return RECOVERY_RECEIPT_ACTION_RETRY_CONTINUATION
    return RECOVERY_RECEIPT_ACTION_RETRY_CONTINUATION


def outcome_from_recovery_result_v1(result: Mapping[str, Any]) -> str:
    if bool(result.get("recovered")):
        return RECOVERY_RECEIPT_OUTCOME_RECOVERED
    reason = str(result.get("reason") or "")
    if reason in ("duplicate_resume_receipt", "phase_07_already_completed"):
        return RECOVERY_RECEIPT_OUTCOME_SKIPPED
    return RECOVERY_RECEIPT_OUTCOME_FAILED


def persist_stalled_recovery_receipt_v1(
    session: Session,
    *,
    continuation: CortexPipelineContinuationState,
    operator_action: str,
    result: Mapping[str, Any],
    recommendation: str | None = None,
) -> dict[str, Any]:
    """Persist receipt for ``recover_stalled_pipeline_v1`` exit."""
    action = normalize_stalled_recovery_action_v1(
        operator_action,
        reason=str(result.get("reason") or "") or None,
        recommendation=recommendation,
    )
    outcome = outcome_from_recovery_result_v1(result)
    return persist_recovery_receipt_v1(
        session,
        continuation=continuation,
        action=action,
        outcome=outcome,
        extra={
            "operator_action": operator_action,
            "reason": result.get("reason"),
            PHASE085_RESUME_RECEIPT_HASH_FIELD_V1: result.get("resume_receipt_hash"),
        },
    )


def build_recovery_receipt_catalog_v1() -> dict[str, Any]:
    """Doctrine catalog for recovery receipts (P085-08)."""
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_recovery_receipt_runtime_schema_version": int(
            PHASE085_RECOVERY_RECEIPT_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_RECOVERY_RECEIPT_SPEC_REF_V1,
        "primary_gate_id": GP085_REC01_GATE_ID_V1,
        "recovery_receipt_action_ids": list(RECOVERY_RECEIPT_ACTION_IDS_V1),
        "recovery_receipt_outcome_ids": list(RECOVERY_RECEIPT_OUTCOME_IDS_V1),
        "required_fields": list(RECOVERY_RECEIPT_REQUIRED_FIELDS_V1),
        "storage_path": "continuation.detail_json.recovery_receipts[]",
        "max_receipts_retained": int(MAX_RECOVERY_RECEIPTS_PER_CONTINUATION_V1),
        "digest_function": "compute_recovery_receipt_digest_v1",
        "operational_metrics": list(_RECOVERY_RECEIPT_METRICS_V1.keys()),
    }


def verify_gp085_rec01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_recovery_receipt_catalog_v1()
    if cat["primary_gate_id"] != GP085_REC01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if set(cat["recovery_receipt_action_ids"]) != set(RECOVERY_RECEIPT_ACTION_IDS_V1):
        errors.append("action_ids_mismatch")
    if set(cat["recovery_receipt_outcome_ids"]) != set(RECOVERY_RECEIPT_OUTCOME_IDS_V1):
        errors.append("outcome_ids_mismatch")

    tid = uuid.uuid4()
    prid = uuid.uuid4()
    nonce = "nonce-test"
    r1 = build_recovery_receipt_v1(
        tenant_id=tid,
        pipeline_run_id=prid,
        action=RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07,
        continuation_nonce=nonce,
        outcome=RECOVERY_RECEIPT_OUTCOME_RECOVERED,
        prior_resume_receipt_hash=None,
    )
    r2 = build_recovery_receipt_v1(
        tenant_id=tid,
        pipeline_run_id=prid,
        action=RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07,
        continuation_nonce=nonce,
        outcome=RECOVERY_RECEIPT_OUTCOME_RECOVERED,
        prior_resume_receipt_hash=None,
        recorded_at=r1["recorded_at"],
    )
    if r1[RECOVERY_RECEIPT_DIGEST_FIELD_V1] != r2[RECOVERY_RECEIPT_DIGEST_FIELD_V1]:
        errors.append("digest_not_deterministic")

    from vector.domains.cortex.substrate_pipeline import stalled_pipeline_recovery as rec_mod

    rec_src = inspect.getsource(rec_mod.recover_stalled_pipeline_v1)
    if (
        "persist_stalled_recovery_receipt_v1" not in rec_src
        and "_finish_stalled_recovery_v1" not in rec_src
    ):
        errors.append("stalled_recovery_missing_receipt_persist")

    from vector.domains.cortex.substrate_pipeline import pipeline_continuation as cont_mod

    resume_src = inspect.getsource(cont_mod.resume_pipeline_after_tcre_completion_v1)
    if "persist_recovery_receipt_v1" not in resume_src:
        errors.append("resume_pipeline_missing_receipt_persist")

    passed = not errors
    return {
        "id": GP085_REC01_GATE_ID_V1,
        "name": "cesp_recovery_receipts",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
