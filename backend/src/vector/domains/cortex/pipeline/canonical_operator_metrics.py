"""Canonical operator metrics — drainable primary, raw−mat diagnostic only."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.candidate_selection import (
    list_untreated_routable_count_estimate,
)
from vector.domains.cortex.canonical.forward_progress.deferral_store import count_deferrals
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

OPERATOR_KPI_PRIMARY_DRAINABLE_V1 = "drainable_routable_estimate"
OPERATOR_KPI_DEPRECATED_RAW_GAP_V1 = "raw_minus_mat_admin_gap"


def snapshot_canonical_operator_metrics_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Fast canonical operator counts for admin surfaces (no full completeness scan)."""
    raw_total = int(
        session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(RawIngestionRecord.tenant_id == tenant_id)
        )
        or 0
    )
    mat_total = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        )
        or 0
    )
    raw_minus_mat_admin_gap = max(0, raw_total - mat_total)

    bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
    untreated_routable_estimate = 0
    drainable_routable_estimate = 0
    deferral_counts: dict[str, int] = {}
    if bundle_id is not None:
        untreated_routable_estimate = int(
            list_untreated_routable_count_estimate(
                session, tenant_id=tenant_id, bundle_id=bundle_id
            )
            or 0
        )
        drainable_routable_estimate = int(
            list_untreated_routable_count_estimate(
                session,
                tenant_id=tenant_id,
                bundle_id=bundle_id,
                drainable_only=True,
            )
            or 0
        )
        deferral_counts = count_deferrals(session, tenant_id=tenant_id, bundle_id=bundle_id)

    return {
        "bundle_id": str(bundle_id) if bundle_id is not None else None,
        "raw_count": raw_total,
        "canonicalized_count": mat_total,
        "raw_minus_mat_admin_gap": raw_minus_mat_admin_gap,
        "untreated_routable_estimate": untreated_routable_estimate,
        "drainable_routable_estimate": drainable_routable_estimate,
        "deferral_counts": deferral_counts,
        "operator_kpi_primary": OPERATOR_KPI_PRIMARY_DRAINABLE_V1,
        "operator_kpi_deprecated": OPERATOR_KPI_DEPRECATED_RAW_GAP_V1,
    }


def _canonical_operator_backlog_count(metrics: dict[str, Any]) -> int:
    """Primary admin backlog = drainable routable (not raw−mat vanity gap)."""
    return int(metrics.get("drainable_routable_estimate") or 0)
