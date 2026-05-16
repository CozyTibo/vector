"""Live chronology projection over canonical materializations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from vector.domains.cortex.reasoning.chronology_legality import (
    project_chronology_legality_class_v1,
)
from vector.domains.cortex.reasoning.interval_continuity import REASONING_CHRONOLOGY_RECEIPT_TYPE
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    REASONING_CANON_VERSION_V1,
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)


def chronology_snapshot_from_materialization_v1(
    mat: CortexCanonicalTransformMaterialization,
) -> dict[str, Any]:
    """Deterministic snapshot booleans from canonical row (no wall clock)."""
    has_order = bool((mat.temporal_ordering_key or "").strip())
    replay_safe_ordering = "strict" if has_order else "partial"
    skew_detected = bool(
        mat.observed_at is not None
        and mat.occurred_at is not None
        and mat.observed_at != mat.occurred_at
    )
    late_arrival = bool(
        mat.observed_at is not None
        and mat.occurred_at is not None
        and mat.observed_at > mat.occurred_at
    )
    return {
        "materialization_id": str(mat.id),
        "bundle_id": mat.bundle_id,
        "replay_safe_ordering": replay_safe_ordering,
        "skew_detected": skew_detected,
        "late_arrival": late_arrival,
        "export_sequence_conflict": False,
        "active_conflict_classes": [],
    }


def reduce_chronology_rows_v1(
    materializations: Sequence[CortexCanonicalTransformMaterialization],
    *,
    policy: Mapping[str, Any],
    tcre_policy_bundle_digest: str,
) -> list[dict[str, Any]]:
    """Project chronology legality + receipt body per materialization (stable sort input)."""
    rows: list[dict[str, Any]] = []
    for mat in materializations:
        snapshot = chronology_snapshot_from_materialization_v1(mat)
        legality_class, matched_idx, partitioned = project_chronology_legality_class_v1(
            snapshot,
            policy,
        )
        receipt_body = {
            "receipt_type": REASONING_CHRONOLOGY_RECEIPT_TYPE,
            "reasoning_canon_version_v1": REASONING_CANON_VERSION_V1,
            "materialization_id": str(mat.id),
            "replay_safe_ordering": str(snapshot["replay_safe_ordering"]),
            "chronology_legality_class": legality_class,
            "matched_projection_row_index": matched_idx,
            "partitioned_exception_applied": partitioned,
            "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
            "chronology_projection_snapshot": dict(snapshot),
        }
        digest = hash_reasoning_canonical_json_sha256_v1(receipt_body)
        rows.append(
            {
                "materialization_id": str(mat.id),
                "snapshot": snapshot,
                "chronology_legality_class": legality_class,
                "matched_projection_row_index": matched_idx,
                "partitioned_exception_applied": partitioned,
                "receipt_body": receipt_body,
                "receipt_digest": digest,
            }
        )
    return rows
