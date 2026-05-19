"""Phase 08.5 P085-07 — async durability + dead-letter (**G-P085-DLQ-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-recovery-continuity-doctrine.md``.
Persistence: ``vector.domains.cortex.substrate_pipeline.pipeline_dead_letter``.
"""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
    PHASE085_RESUME_RECEIPT_HASH_FIELD_V1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_dead_letter import (
    FAILURE_CLASS_IDS_V1,
    RECOVERY_ACTION_IDS_V1,
)

PHASE085_RECOVERY_CONTINUITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_RECOVERY_CONTINUITY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-recovery-continuity-doctrine.md"
)

GP085_DLQ01_GATE_ID_V1: Final[str] = "G-P085-DLQ-01"

_DLQ_METRIC_NAMES_V1: Final[tuple[str, ...]] = (
    "substrate_dlq_open_total",
    "substrate_dlq_resolved_total",
    "substrate_dlq_auto_retry_blocked_total",
)

_DLQ_METRICS_V1: dict[str, int] = {name: 0 for name in _DLQ_METRIC_NAMES_V1}


class RecoveryContinuityError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def increment_dlq_metric_v1(metric_name: str, *, delta: int = 1) -> None:
    if metric_name in _DLQ_METRICS_V1:
        _DLQ_METRICS_V1[metric_name] += max(1, int(delta))


def snapshot_dlq_metrics_v1() -> dict[str, int]:
    return dict(_DLQ_METRICS_V1)


def build_recovery_continuity_catalog_v1() -> dict[str, Any]:
    """Doctrine catalog for DLQ + recovery continuity (P085-07)."""
    from vector.domains.cortex.substrate_pipeline.pipeline_dead_letter import (
        get_dlq_max_auto_retries_per_receipt_v1,
    )

    return {
        "surface_kind": "doctrine_catalog",
        "phase085_recovery_continuity_runtime_schema_version": int(
            PHASE085_RECOVERY_CONTINUITY_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_RECOVERY_CONTINUITY_SPEC_REF_V1,
        "primary_gate_id": GP085_DLQ01_GATE_ID_V1,
        "failure_class_ids": list(FAILURE_CLASS_IDS_V1),
        "recovery_action_ids": list(RECOVERY_ACTION_IDS_V1),
        "dlq_required_fields": [
            "dead_letter_id",
            "pipeline_run_id",
            "phase_id",
            "async_job_id",
            "failure_class",
            "replay_safe",
            "recovery_actions",
        ],
        "resume_receipt_hash_field": PHASE085_RESUME_RECEIPT_HASH_FIELD_V1,
        "n_max_auto_retries_per_receipt": get_dlq_max_auto_retries_per_receipt_v1(),
        "durable_table": "cortex_substrate_pipeline_dead_letters",
        "runtime_package": "vector.domains.cortex.substrate_pipeline.pipeline_dead_letter",
        "operational_metrics": list(_DLQ_METRIC_NAMES_V1),
        "dlq_rule": "DLQ entry MUST NOT auto-retry more than N_max times per resume_receipt_hash",
    }


def verify_gp085_dlq01_static() -> dict[str, Any]:
    from vector.domains.cortex.substrate_pipeline.pipeline_dead_letter import (
        get_dlq_max_auto_retries_per_receipt_v1,
    )

    errors: list[str] = []
    cat = build_recovery_continuity_catalog_v1()
    if cat["primary_gate_id"] != GP085_DLQ01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if set(cat["failure_class_ids"]) != set(FAILURE_CLASS_IDS_V1):
        errors.append("failure_class_ids_mismatch")
    if len(cat["failure_class_ids"]) != len(FAILURE_CLASS_IDS_V1):
        errors.append("failure_class_count_mismatch")
    if set(cat["recovery_action_ids"]) != set(RECOVERY_ACTION_IDS_V1):
        errors.append("recovery_action_ids_mismatch")
    if int(get_dlq_max_auto_retries_per_receipt_v1()) < 1:
        errors.append("n_max_auto_retries_invalid")

    from vector.domains.cortex.substrate_pipeline import pipeline_dead_letter as dlq_mod

    for name in (
        "record_pipeline_dead_letter_v1",
        "assert_dlq_auto_retry_budget_v1",
        "list_open_dead_letters_v1",
        "resolve_dead_letter_v1",
    ):
        if not callable(getattr(dlq_mod, name, None)):
            errors.append(f"missing_dlq_symbol:{name}")

    passed = not errors
    return {
        "id": GP085_DLQ01_GATE_ID_V1,
        "name": "cesp_substrate_dead_letter",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
