"""Phase 08.5 P085-15 — traversal retry + frontier healing (**G-P085-WALK-02**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-traversal-completion-doctrine.md`` §Retry.
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Mapping
from typing import Any, Final, cast

from sqlalchemy.orm import Session

from vector.domains.cortex.identity.projection_export import build_org_graph_projection_export_document
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    GP085_WALK01_GATE_ID_V1,
)
from vector.domains.cortex.retrieval.retrieval_skip_registry import (
    RET_SKIP_WALK_INCOMPLETE_V1,
)
from vector.domains.cortex.substrate_pipeline.substrate_traversal_execution import (
    build_reference_walk_payload_v1,
)
from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1
from vector.domains.cortex.traversal.runtime_execution_model import RuntimeExecutionModelError
from vector.domains.cortex.traversal.walk_api_contract import WalkApiRecordV1
from vector.domains.cortex.traversal.walk_policy import validate_walk_policy_for_request_v1

PHASE085_TRAVERSAL_RETRY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_TRAVERSAL_RETRY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-traversal-completion-doctrine.md"
)

GP085_WALK02_GATE_ID_V1: Final[str] = "G-P085-WALK-02"

CELERY_TRAVERSAL_RETRY_TASK_NAME_V1: Final[str] = (
    "vector.cortex.operational_runtime.traversal_retry_and_heal_pass"
)

FAILURE_TRANSIENT_STORE_V1: Final[str] = "transient_store_error"
FAILURE_WALK_INCOMPLETE_V1: Final[str] = "walk_incomplete"
FAILURE_FRONTIER_COLLAPSE_V1: Final[str] = "frontier_collapse"

RETRY_ACTION_EXPONENTIAL_BACKOFF_V1: Final[str] = "exponential_backoff_retry"
RETRY_ACTION_EXPLAIN_ONLY_V1: Final[str] = "explain_only"
RETRY_ACTION_FRONTIER_HEAL_V1: Final[str] = "frontier_heal_pass"

RETRY_POLICY_BY_FAILURE_V1: Final[dict[str, str]] = {
    FAILURE_TRANSIENT_STORE_V1: RETRY_ACTION_EXPONENTIAL_BACKOFF_V1,
    FAILURE_WALK_INCOMPLETE_V1: RETRY_ACTION_EXPLAIN_ONLY_V1,
    FAILURE_FRONTIER_COLLAPSE_V1: RETRY_ACTION_FRONTIER_HEAL_V1,
}

_WALK_INCOMPLETE_TERMINATION_REASONS_V1: Final[frozenset[str]] = frozenset(
    {
        "policy_rejected",
        "invalid_edge_at_t",
        "dangling_evidence",
        "import_hash_mismatch",
        "error_internal",
    }
)

_FRONTIER_COLLAPSE_TERMINATION_REASONS_V1: Final[frozenset[str]] = frozenset(
    {
        "empty_frontier",
        "budget_exhausted",
    }
)

CESP_WALK_RETRY_DETAIL_KEY_V1: Final[str] = "cesp_walk_retry_v1"


class SubstrateTraversalRetryError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_traversal_retry_max_attempts_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_traversal_retry_max_attempts))
    except Exception:  # noqa: BLE001
        return 3


def get_traversal_retry_backoff_base_seconds_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_traversal_retry_backoff_base_seconds))
    except Exception:  # noqa: BLE001
        return 2


def get_traversal_frontier_heal_multiplier_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(2, int(get_settings().cortex_traversal_frontier_heal_multiplier))
    except Exception:  # noqa: BLE001
        return 2


def get_traversal_retry_pass_limit_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_traversal_retry_pass_limit))
    except Exception:  # noqa: BLE001
        return 32


def compute_retry_backoff_seconds_v1(attempt: int) -> int:
    """Exponential backoff for transient store retries (attempt is 1-based)."""
    base = get_traversal_retry_backoff_base_seconds_v1()
    exp = max(0, int(attempt) - 1)
    return int(base * (2**exp))


def should_retry_transient_failure_v1(*, attempt: int) -> bool:
    return int(attempt) <= get_traversal_retry_max_attempts_v1()


def _hop_count_from_record_v1(record: WalkApiRecordV1) -> int:
    payload = dict(record.walk_payload or {})
    telemetry = dict(payload.get("telemetry") or {})
    if telemetry.get("hops_emitted") is not None:
        return int(telemetry["hops_emitted"])
    hb = dict((payload.get("walk_result") or {}).get("hash_body") or {})
    return len(hb.get("hop_receipts") or [])


def _termination_reason_from_record_v1(record: WalkApiRecordV1) -> str:
    payload = dict(record.walk_payload or {})
    hb = dict((payload.get("walk_result") or {}).get("hash_body") or {})
    return str(hb.get("termination_reason") or "").strip()


def _retry_detail_from_request_v1(request_body: dict[str, Any]) -> dict[str, Any]:
    raw = request_body.get(CESP_WALK_RETRY_DETAIL_KEY_V1)
    return dict(raw) if isinstance(raw, dict) else {}


def _merge_retry_detail_v1(
    request_body: dict[str, Any],
    *,
    patch: dict[str, Any],
) -> dict[str, Any]:
    body = dict(request_body)
    detail = _retry_detail_from_request_v1(body)
    detail.update(patch)
    body[CESP_WALK_RETRY_DETAIL_KEY_V1] = detail
    return body


def classify_walk_failure_v1(
    record: WalkApiRecordV1,
    *,
    error: BaseException | None = None,
) -> tuple[str | None, str]:
    """Map a walk record to doctrine failure class + reason code."""
    if record.status == "failed":
        if error is not None:
            return FAILURE_TRANSIENT_STORE_V1, type(error).__name__
        return FAILURE_TRANSIENT_STORE_V1, "walk_status_failed"

    if record.status != "completed":
        return None, ""

    tr = _termination_reason_from_record_v1(record)
    hops = _hop_count_from_record_v1(record)

    if tr in _WALK_INCOMPLETE_TERMINATION_REASONS_V1:
        return FAILURE_WALK_INCOMPLETE_V1, tr

    if tr in _FRONTIER_COLLAPSE_TERMINATION_REASONS_V1 and hops == 0:
        return FAILURE_FRONTIER_COLLAPSE_V1, f"{tr}_zero_hops"

    if error is not None:
        return FAILURE_TRANSIENT_STORE_V1, type(error).__name__

    return None, ""


def build_walk_failure_explanation_v1(
    *,
    walk_id: uuid.UUID,
    failure_class: str,
    reason_code: str,
    retry_action: str,
    ret_skip_code: str | None = None,
) -> dict[str, Any]:
    """Operator-facing explain payload (no retry for ``walk_incomplete``)."""
    return {
        "gate_id": GP085_WALK02_GATE_ID_V1,
        "walk_id": str(walk_id),
        "failure_class": failure_class,
        "reason_code": reason_code,
        "retry_action": retry_action,
        "ret_skip_code": ret_skip_code,
        "explained": failure_class == FAILURE_WALK_INCOMPLETE_V1,
    }


def _healed_walk_policy_v1(policy: dict[str, Any]) -> dict[str, Any]:
    mult = get_traversal_frontier_heal_multiplier_v1()
    healed = dict(policy)
    for key, cap in (
        ("max_frontier", 256),
        ("max_edges_visited", 2000),
        ("max_hops", 32),
    ):
        if key in healed:
            healed[key] = min(int(cap), int(healed[key]) * mult)
    return healed


def _reexecute_walk_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    record: WalkApiRecordV1,
    policy_override: dict[str, Any] | None = None,
    parent_walk_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    export_doc = build_org_graph_projection_export_document(session, tenant_id=tenant_id)
    inner = export_doc.get("projection")
    if not isinstance(inner, dict):
        raise SubstrateTraversalRetryError("missing_graph_projection")

    request_body = dict(record.request_body or {})
    if policy_override is not None:
        request_body["walk_policy"] = dict(policy_override)
    starts = request_body.get("start_node_ids")
    if not isinstance(starts, list) or not starts:
        raise SubstrateTraversalRetryError("missing_start_node_ids")

    validate_walk_policy_for_request_v1(
        cast(Mapping[str, Any], request_body["walk_policy"]),
        walk_execution_strategy=str(request_body.get("walk_execution_strategy") or "ONLINE_OBSERVED"),
        exploration_mode=bool(request_body.get("exploration_mode")),
        enforce_sync_caps=False,
    )

    start = str(starts[0]).strip()
    payload = build_reference_walk_payload_v1(
        request_body,
        tenant_id=tenant_id,
        projection_inner=cast(Mapping[str, Any], inner),
        start_node_id=start,
    )

    from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
        hash_reasoning_canonical_json_sha256_v1,
    )

    store = resolve_octs_walk_store_v1(session)
    new_walk_id = uuid.uuid4()
    idem_suffix = hash_reasoning_canonical_json_sha256_v1(
        {
            "parent": str(parent_walk_id or record.walk_id),
            "retry_lane": "cesp_walk02",
            "start": start,
        }
    )[:48]
    base_idem = str(record.idempotency_key or "cesp-retry")
    idem = f"{base_idem}:{idem_suffix}"

    replay_lineage = {
        "replay_of_walk_id": str(parent_walk_id or record.walk_id),
        "original_walk_result_hash": str(
            ((record.walk_payload or {}).get("walk_result") or {}).get("walk_result_hash") or ""
        ),
    }

    store.insert_completed_sync(
        tenant_id=tenant_id,
        walk_id=new_walk_id,
        request_body=_merge_retry_detail_v1(
            request_body,
            patch={
                "healed_from_walk_id": str(record.walk_id),
                "parent_walk_id": str(parent_walk_id or record.walk_id),
            },
        ),
        walk_payload=payload,
        idempotency_key=idem,
        replay_lineage=replay_lineage,
    )
    session.flush()
    return {
        "new_walk_id": str(new_walk_id),
        "parent_walk_id": str(record.walk_id),
        "termination_reason": _termination_reason_from_record_v1(
            WalkApiRecordV1(
                walk_id=new_walk_id,
                tenant_id=tenant_id,
                status="completed",
                request_body=request_body,
                walk_payload=payload,
            )
        ),
    }


def retry_transient_walk_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    record: WalkApiRecordV1,
    attempt: int,
) -> dict[str, Any]:
    """Retry a transient store failure with bounded exponential backoff policy."""
    if not should_retry_transient_failure_v1(attempt=attempt):
        return {
            "action": RETRY_ACTION_EXPONENTIAL_BACKOFF_V1,
            "attempt": attempt,
            "skipped": True,
            "reason": "max_attempts_exceeded",
        }
    try:
        out = _reexecute_walk_v1(
            session,
            tenant_id=tenant_id,
            record=record,
            parent_walk_id=record.walk_id,
        )
    except (RuntimeExecutionModelError, SubstrateTraversalRetryError, ValueError) as exc:
        return {
            "action": RETRY_ACTION_EXPONENTIAL_BACKOFF_V1,
            "attempt": attempt,
            "failed": True,
            "error": str(exc),
            "backoff_seconds": compute_retry_backoff_seconds_v1(attempt + 1),
        }
    return {
        "action": RETRY_ACTION_EXPONENTIAL_BACKOFF_V1,
        "attempt": attempt,
        "succeeded": True,
        "backoff_seconds": compute_retry_backoff_seconds_v1(attempt),
        **out,
    }


def run_frontier_heal_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    record: WalkApiRecordV1,
) -> dict[str, Any]:
    """Frontier heal — deterministic policy boost + re-execute walk."""
    policy = dict((record.request_body or {}).get("walk_policy") or {})
    healed_policy = _healed_walk_policy_v1(policy)
    try:
        out = _reexecute_walk_v1(
            session,
            tenant_id=tenant_id,
            record=record,
            policy_override=healed_policy,
            parent_walk_id=record.walk_id,
        )
    except (RuntimeExecutionModelError, SubstrateTraversalRetryError, ValueError) as exc:
        return {
            "action": RETRY_ACTION_FRONTIER_HEAL_V1,
            "failed": True,
            "error": str(exc),
            "healed_policy": healed_policy,
        }
    return {
        "action": RETRY_ACTION_FRONTIER_HEAL_V1,
        "succeeded": True,
        "healed_policy": healed_policy,
        **out,
    }


def list_walk_records_for_retry_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int | None = None,
) -> list[WalkApiRecordV1]:
    """Walk rows eligible for retry/heal classification."""
    lim = limit if limit is not None else get_traversal_retry_pass_limit_v1()
    store = resolve_octs_walk_store_v1(session)
    records = store.list_walk_records_for_tenant_v1(tenant_id)
    eligible: list[WalkApiRecordV1] = []
    for rec in records:
        failure_class, _ = classify_walk_failure_v1(rec)
        if failure_class is not None:
            eligible.append(rec)
        if len(eligible) >= lim:
            break
    return eligible


def apply_walk_failure_policy_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    record: WalkApiRecordV1,
) -> dict[str, Any]:
    """Apply doctrine retry policy for one walk record."""
    failure_class, reason_code = classify_walk_failure_v1(record)
    if failure_class is None:
        return {"skipped": True, "reason": "not_retryable"}

    action = RETRY_POLICY_BY_FAILURE_V1[failure_class]
    detail = _retry_detail_from_request_v1(dict(record.request_body or {}))
    attempt = int(detail.get("retry_attempt_count") or 0) + 1

    if failure_class == FAILURE_WALK_INCOMPLETE_V1:
        explanation = build_walk_failure_explanation_v1(
            walk_id=record.walk_id,
            failure_class=failure_class,
            reason_code=reason_code,
            retry_action=action,
            ret_skip_code=RET_SKIP_WALK_INCOMPLETE_V1,
        )
        return {
            "failure_class": failure_class,
            "action": action,
            "explanation": explanation,
        }

    if failure_class == FAILURE_TRANSIENT_STORE_V1:
        result = retry_transient_walk_v1(
            session,
            tenant_id=tenant_id,
            record=record,
            attempt=attempt,
        )
        return {
            "failure_class": failure_class,
            "action": action,
            "attempt": attempt,
            **result,
        }

    if failure_class == FAILURE_FRONTIER_COLLAPSE_V1:
        result = run_frontier_heal_pass_v1(session, tenant_id=tenant_id, record=record)
        return {
            "failure_class": failure_class,
            "action": action,
            **result,
        }

    return {"skipped": True, "reason": "unknown_failure_class"}


def run_traversal_retry_and_heal_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int | None = None,
) -> dict[str, Any]:
    """Scan tenant walks and apply **G-P085-WALK-02** policies."""
    records = list_walk_records_for_retry_v1(session, tenant_id=tenant_id, limit=limit)
    outcomes: list[dict[str, Any]] = []
    for rec in records:
        outcomes.append(
            apply_walk_failure_policy_v1(session, tenant_id=tenant_id, record=rec)
        )

    by_action: dict[str, int] = {}
    for o in outcomes:
        act = str(o.get("action") or o.get("reason") or "skipped")
        by_action[act] = by_action.get(act, 0) + 1

    return {
        "gate_id": GP085_WALK02_GATE_ID_V1,
        "related_gate_id": GP085_WALK01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "records_scanned": len(records),
        "outcomes": outcomes,
        "outcome_counts": by_action,
        "retry_max_attempts": get_traversal_retry_max_attempts_v1(),
        "frontier_heal_multiplier": get_traversal_frontier_heal_multiplier_v1(),
    }


def schedule_traversal_retry_and_heal_pass_v1(
    *,
    tenant_id: uuid.UUID,
    countdown: int | None = None,
    session: Session | None = None,
) -> dict[str, Any]:
    """M9: synchronous inline pass only (admin; not execution slice)."""
    _ = countdown

    if session is not None:
        pass_out = run_traversal_retry_and_heal_pass_v1(session, tenant_id=tenant_id)
        return {"scheduled": True, "path": "inline_execution_slice", "pass": pass_out}
    from vector.infrastructure.db.session import session_scope

    with session_scope() as scoped:
        pass_out = run_traversal_retry_and_heal_pass_v1(scoped, tenant_id=tenant_id)
        scoped.commit()
        return {"scheduled": True, "path": "inline_execution_slice", "pass": pass_out}


def build_substrate_traversal_retry_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_traversal_retry_runtime_schema_version": int(
            PHASE085_TRAVERSAL_RETRY_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_TRAVERSAL_RETRY_SPEC_REF_V1,
        "primary_gate_id": GP085_WALK02_GATE_ID_V1,
        "failure_classes": [
            FAILURE_TRANSIENT_STORE_V1,
            FAILURE_WALK_INCOMPLETE_V1,
            FAILURE_FRONTIER_COLLAPSE_V1,
        ],
        "retry_policy_by_failure": dict(RETRY_POLICY_BY_FAILURE_V1),
        "retry_max_attempts": get_traversal_retry_max_attempts_v1(),
        "retry_backoff_base_seconds": get_traversal_retry_backoff_base_seconds_v1(),
        "frontier_heal_multiplier": get_traversal_frontier_heal_multiplier_v1(),
        "celery_task_name": CELERY_TRAVERSAL_RETRY_TASK_NAME_V1,
        "pass_entrypoint": "run_traversal_retry_and_heal_pass_v1",
        "runtime_package": "vector.domains.cortex.operational_runtime.substrate_traversal_retry",
    }


def verify_gp085_walk02_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_traversal_retry_catalog_v1()
    if cat["retry_policy_by_failure"][FAILURE_WALK_INCOMPLETE_V1] != RETRY_ACTION_EXPLAIN_ONLY_V1:
        errors.append("walk_incomplete_must_be_explain_only")

    if compute_retry_backoff_seconds_v1(1) != get_traversal_retry_backoff_base_seconds_v1():
        errors.append("backoff_base_mismatch")
    if compute_retry_backoff_seconds_v1(3) != get_traversal_retry_backoff_base_seconds_v1() * 4:
        errors.append("backoff_exponential_mismatch")

    if not should_retry_transient_failure_v1(attempt=1):
        errors.append("should_retry_attempt_1")
    if should_retry_transient_failure_v1(attempt=99):
        errors.append("should_not_retry_attempt_99")

    src = inspect.getsource(classify_walk_failure_v1)
    if "random" in src.lower():
        errors.append("probabilistic_retry_forbidden")

    import importlib.util

    if importlib.util.find_spec("app.tasks.cortex_substrate_traversal_retry") is not None:
        errors.append("celery_traversal_retry_module_must_be_deleted_m9")

    passed = not errors
    return {
        "id": GP085_WALK02_GATE_ID_V1,
        "name": "cesp_substrate_traversal_retry",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
