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
) -> dict[str, Any]:
    velocity = (
        round(float(total_succeeded) / (float(elapsed_ms) / 1000.0), 4)
        if elapsed_ms > 0 and total_succeeded > 0
        else 0.0
    )
    deferred_total = int(deferral_counts.get("deferred_total") or 0)
    return {
        "untreated_routable_estimate": int(untreated_estimate),
        "deferred_total": deferred_total,
        "deferred_waiting_cooldown": int(deferral_counts.get("deferred_waiting_cooldown") or 0),
        "deferred_retry_ready": int(deferral_counts.get("deferred_retry_ready") or 0),
        "convergence_delta_succeeded": int(total_succeeded),
        "progress_velocity_rows_per_second": velocity,
        "topology_blockers_deferred": deferred_total,
    }
