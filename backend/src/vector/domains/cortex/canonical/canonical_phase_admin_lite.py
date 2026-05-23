"""Fast canonical fields for pipeline phase summary-detail (operator cards only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.pipeline.canonical_operator_metrics import (
    snapshot_canonical_operator_metrics_v1,
)
from vector.infrastructure.db.models.cortex_canonical_failure_case import CortexCanonicalFailureCase
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_canonical_verification_run import (
    CortexCanonicalVerificationRun,
)

_VERIFICATION_STALE_HOURS = 48


def _verification_freshness(last_ver: CortexCanonicalVerificationRun | None) -> str:
    if last_ver is None:
        return "never_run"
    if last_ver.passed is not True:
        return "failed"
    created = last_ver.created_at
    if created is None:
        return "unknown"
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    age = datetime.now(UTC) - created
    if age > timedelta(hours=_VERIFICATION_STALE_HOURS):
        return "stale"
    return "fresh"


def build_canonical_phase_summary_metrics_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    operator_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Lightweight canonical metrics for admin phase tab (no full control plane)."""
    mat_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        )
        or 0
    )
    failure_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalFailureCase)
            .where(
                CortexCanonicalFailureCase.tenant_id == tenant_id,
                CortexCanonicalFailureCase.active.is_(True),
            )
        )
        or 0
    )
    last_ver = session.scalar(
        select(CortexCanonicalVerificationRun)
        .where(CortexCanonicalVerificationRun.tenant_id == tenant_id)
        .order_by(
            CortexCanonicalVerificationRun.created_at.desc(),
            CortexCanonicalVerificationRun.id.desc(),
        )
        .limit(1)
    )
    freshness = _verification_freshness(last_ver)
    metrics = operator_metrics or snapshot_canonical_operator_metrics_v1(
        session, tenant_id=tenant_id
    )
    untreated_estimate = int(metrics.get("untreated_routable_estimate") or 0)
    drainable_estimate = int(metrics.get("drainable_routable_estimate") or 0)

    health = {
        "materialization_row_count": mat_count,
        "active_canonical_failure_count": failure_count,
        "last_verification_passed": bool(last_ver.passed) if last_ver is not None else None,
        "verification_freshness_label": freshness,
    }
    return {
        "health": health,
        "forward_progress": {
            "untreated_estimate": untreated_estimate,
            "drainable_estimate": drainable_estimate,
        },
        "operator_metrics": metrics,
        "failure_count": failure_count,
    }
