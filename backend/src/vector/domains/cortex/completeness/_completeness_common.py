"""Shared deterministic completeness stage envelope helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

SUBSTRATE_COMPLETENESS_LEDGER_SCHEMA_VERSION: Final[int] = 1

STAGE_IDS: Final[tuple[str, ...]] = (
    "ingestion",
    "canonical",
    "identity",
    "graph",
    "traversal",
    "tcre",
)

SUBSTRATE_STATES: Final[frozenset[str]] = frozenset({"healthy", "degraded", "critical"})
REPLAY_POSTURES: Final[frozenset[str]] = frozenset({"stable", "partial", "unsafe", "unknown"})


def pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(100.0 * numerator / denominator, 2)


def build_stage_envelope_v1(
    *,
    stage_id: str,
    label: str,
    total_objects: int,
    processed_count: int = 0,
    degraded_count: int = 0,
    unresolved_count: int = 0,
    omitted_count: int = 0,
    intentionally_excluded_count: int = 0,
    replay_posture: str = "unknown",
    substrate_state: str = "healthy",
    last_successful_at: str | None = None,
    drift_warnings: list[str] | None = None,
    omission_classes: Mapping[str, int] | None = None,
    detail_route: str,
    metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    total = max(0, int(total_objects))
    degraded = min(max(0, int(degraded_count)), total)
    unresolved = min(max(0, int(unresolved_count)), total - degraded)
    excluded = min(max(0, int(intentionally_excluded_count)), total - degraded - unresolved)
    omitted = max(0, int(omitted_count))
    success = max(0, total - degraded - unresolved - excluded)
    denom = total if total else max(success + degraded + unresolved + excluded, 1)
    body: dict[str, Any] = {
        "schema_version": 1,
        "stage_id": stage_id,
        "label": label,
        "total_objects": total,
        "processed_count": max(0, int(processed_count)),
        "success_count": success,
        "degraded_count": degraded,
        "unresolved_count": unresolved,
        "omitted_count": omitted,
        "intentionally_excluded_count": excluded,
        "success_percent": pct(success, denom),
        "degraded_percent": pct(degraded, denom),
        "unresolved_percent": pct(unresolved, denom),
        "replay_posture": replay_posture if replay_posture in REPLAY_POSTURES else "unknown",
        "substrate_state": substrate_state if substrate_state in SUBSTRATE_STATES else "degraded",
        "last_successful_at": last_successful_at,
        "drift_warnings": list(drift_warnings or []),
        "omission_classes": dict(sorted((omission_classes or {}).items())),
        "detail_route": detail_route,
        "metrics": dict(metrics or {}),
    }
    body["stage_receipt_digest"] = hash_reasoning_canonical_json_sha256_v1(
        {k: v for k, v in body.items() if k != "stage_receipt_digest"}
    )
    return body


def derive_substrate_state_from_stages(stages: Sequence[Mapping[str, Any]]) -> str:
    if any(s.get("substrate_state") == "critical" for s in stages):
        return "critical"
    if any(
        s.get("substrate_state") == "degraded"
        or float(s.get("degraded_percent") or 0) > 5
        or float(s.get("unresolved_percent") or 0) > 10
        for s in stages
    ):
        return "degraded"
    return "healthy"


def derive_global_replay_posture(stages: Sequence[Mapping[str, Any]]) -> str:
    postures = [str(s.get("replay_posture") or "unknown") for s in stages]
    if any(p == "unsafe" for p in postures):
        return "unsafe"
    if any(p in ("partial", "unknown") for p in postures):
        return "partial"
    if all(p == "stable" for p in postures):
        return "stable"
    return "unknown"
