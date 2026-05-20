"""Operator-facing forward-progress metrics for canonical convergence."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session


def build_forward_progress_metrics(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    untreated_estimate: int,
    deferral_counts: dict[str, int],
    total_succeeded: int,
    elapsed_ms: int,
    productive_batches: int = 0,
    topology_only_batches: int = 0,
    progress_density: float = 0.0,
    blocked_pass_ratio: float = 0.0,
    deferral_pressure: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    _ = db, tenant_id, bundle_id
    velocity = (
        round(float(total_succeeded) / (float(elapsed_ms) / 1000.0), 4)
        if elapsed_ms > 0 and total_succeeded > 0
        else 0.0
    )
    deferred_total = int(deferral_counts.get("deferred_total") or 0)
    permanent_orphan = int(deferral_counts.get("deferred_permanent_orphan") or 0)
    return {
        "untreated_routable_estimate": int(untreated_estimate),
        "deferred_total": deferred_total,
        "deferred_waiting_cooldown": int(deferral_counts.get("deferred_waiting_cooldown") or 0),
        "deferred_retry_ready": int(deferral_counts.get("deferred_retry_ready") or 0),
        "deferred_permanent_orphan": permanent_orphan,
        "convergence_delta_succeeded": int(total_succeeded),
        "progress_velocity_rows_per_second": velocity,
        "progress_density_rows_per_batch": float(progress_density),
        "productive_batches": int(productive_batches),
        "topology_only_batches": int(topology_only_batches),
        "blocked_pass_batch_ratio": float(blocked_pass_ratio),
        "topology_blockers_deferred": deferred_total,
        "structural_orphan_pressure": permanent_orphan,
        "deferral_pressure_sample": list(deferral_pressure or []),
    }
