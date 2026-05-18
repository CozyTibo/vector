"""In-process retrieval substrate density metrics (operational observability)."""

from __future__ import annotations

import uuid
from typing import Any, Final

_RETRIEVAL_ROWS_MATERIALIZED_TOTAL_V1: int = 0
_RETRIEVAL_ROWS_SKIPPED_TOTAL_V1: int = 0
_RETRIEVAL_PUBLISH_SUCCESS_V1: int = 0
_RETRIEVAL_PUBLISH_EMPTY_V1: int = 0
_TENANT_ACCEPTANCE_SAMPLES_V1: dict[str, list[float]] = {}


def record_retrieval_materialization_metrics_v1(
    *,
    tenant_id: uuid.UUID,
    accepted_rows: int,
    skipped_rows: int,
    entry_count: int,
) -> None:
    global _RETRIEVAL_ROWS_MATERIALIZED_TOTAL_V1, _RETRIEVAL_ROWS_SKIPPED_TOTAL_V1
    global _RETRIEVAL_PUBLISH_SUCCESS_V1, _RETRIEVAL_PUBLISH_EMPTY_V1
    _RETRIEVAL_ROWS_MATERIALIZED_TOTAL_V1 += max(0, accepted_rows)
    _RETRIEVAL_ROWS_SKIPPED_TOTAL_V1 += max(0, skipped_rows)
    _RETRIEVAL_PUBLISH_SUCCESS_V1 += 1
    if entry_count <= 0:
        _RETRIEVAL_PUBLISH_EMPTY_V1 += 1
    total = accepted_rows + skipped_rows
    rate = float(accepted_rows) / float(total) if total > 0 else 0.0
    key = str(tenant_id)
    samples = _TENANT_ACCEPTANCE_SAMPLES_V1.setdefault(key, [])
    samples.append(rate)
    if len(samples) > 64:
        del samples[:-64]


def get_retrieval_density_metrics_snapshot_v1() -> dict[str, Any]:
    total_mat = _RETRIEVAL_ROWS_MATERIALIZED_TOTAL_V1
    total_skip = _RETRIEVAL_ROWS_SKIPPED_TOTAL_V1
    denom = total_mat + total_skip
    acceptance_rate = float(total_mat) / float(denom) if denom > 0 else 0.0
    publish_total = _RETRIEVAL_PUBLISH_SUCCESS_V1
    empty_rate = (
        float(_RETRIEVAL_PUBLISH_EMPTY_V1) / float(publish_total) if publish_total > 0 else 0.0
    )
    per_tenant: dict[str, float] = {}
    for tid, samples in _TENANT_ACCEPTANCE_SAMPLES_V1.items():
        if samples:
            per_tenant[tid] = sum(samples) / len(samples)
    return {
        "retrieval_rows_materialized_total": total_mat,
        "retrieval_rows_skipped_total": total_skip,
        "retrieval_row_acceptance_rate": acceptance_rate,
        "retrieval_density_per_tenant": per_tenant,
        "retrieval_publish_success_rate": 1.0 if publish_total > 0 else 0.0,
        "retrieval_epoch_empty_rate": empty_rate,
        "retrieval_publish_total": publish_total,
    }


def reset_retrieval_density_metrics_for_tests_v1() -> None:
    global _RETRIEVAL_ROWS_MATERIALIZED_TOTAL_V1, _RETRIEVAL_ROWS_SKIPPED_TOTAL_V1
    global _RETRIEVAL_PUBLISH_SUCCESS_V1, _RETRIEVAL_PUBLISH_EMPTY_V1
    _RETRIEVAL_ROWS_MATERIALIZED_TOTAL_V1 = 0
    _RETRIEVAL_ROWS_SKIPPED_TOTAL_V1 = 0
    _RETRIEVAL_PUBLISH_SUCCESS_V1 = 0
    _RETRIEVAL_PUBLISH_EMPTY_V1 = 0
    _TENANT_ACCEPTANCE_SAMPLES_V1.clear()
