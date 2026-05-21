"""Deterministic canonical drain receipt hash (TRUE P0 golden replay)."""

from __future__ import annotations

import uuid
from typing import Any

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

CANONICAL_DRAIN_RECEIPT_VERSION: str = "canonical_drain_receipt_v1"


def build_canonical_drain_receipt_hash_v1(
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    canonical_outcome: str,
    total_succeeded: int,
    total_failed_rows: int,
    batches_run: int,
    batch_ids: list[int],
    deferral_snapshot_id: str | None = None,
) -> str:
    """Stable hash over drain slice facts (independent of pass rotation metadata)."""
    payload: dict[str, Any] = {
        "deterministic_version": CANONICAL_DRAIN_RECEIPT_VERSION,
        "tenant_id": str(tenant_id),
        "bundle_id": bundle_id,
        "canonical_outcome": canonical_outcome,
        "total_succeeded": int(total_succeeded),
        "total_failed_rows": int(total_failed_rows),
        "batches_run": int(batches_run),
        "batch_ids": sorted(int(x) for x in batch_ids),
        "deferral_snapshot_id": deferral_snapshot_id or "",
    }
    return hash_reasoning_canonical_json_sha256_v1(payload)
