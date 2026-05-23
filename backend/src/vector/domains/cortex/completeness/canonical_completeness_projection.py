"""Canonical materialization completeness (raw → canonical lineage accounting)."""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.candidate_selection import (
    list_untreated_routable_count_estimate,
)
from vector.domains.cortex.canonical.forward_progress.deferral_store import count_deferrals
from vector.domains.cortex.canonical.transform_runtime import (
    resolve_default_bundle_id_for_stub_transform,
)
from vector.domains.cortex.canonical.permanent_orphan_omission_doctrine import (
    evaluate_permanent_orphan_omission_posture_v1,
)
from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1, pct
from vector.infrastructure.db.models.cortex_canonical_failure_case import CortexCanonicalFailureCase
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def project_canonical_completeness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    admin_fast: bool = False,
) -> dict[str, Any]:
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
    failures = list(
        session.scalars(
            select(CortexCanonicalFailureCase).where(
                CortexCanonicalFailureCase.tenant_id == tenant_id,
                CortexCanonicalFailureCase.active.is_(True),
            )
        ).all()
    )
    failure_classes = Counter(c.failure_class for c in failures)
    omission_classes: dict[str, int] = dict(failure_classes)
    unsupported = int(omission_classes.get("unsupported_payload", 0))
    parse_failed = int(omission_classes.get("parse_failure", 0))
    schema_drift = int(omission_classes.get("schema_drift_detected", 0))

    unmaterialized = max(0, raw_total - mat_total)
    if unmaterialized and "reconstruction_skipped_by_policy" not in omission_classes:
        omission_classes["canonical_backlog_unmaterialized"] = unmaterialized

    bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
    untreated_routable_estimate = 0
    drainable_routable_estimate = 0
    deferral_counts: dict[str, int] = {}
    deferral_omission: dict[str, Any] = evaluate_permanent_orphan_omission_posture_v1(
        deferral_counts={}
    )
    if bundle_id and not admin_fast:
        untreated_routable_estimate = list_untreated_routable_count_estimate(
            session, tenant_id=tenant_id, bundle_id=bundle_id
        )
        drainable_routable_estimate = list_untreated_routable_count_estimate(
            session, tenant_id=tenant_id, bundle_id=bundle_id, drainable_only=True
        )
        deferral_counts = count_deferrals(session, tenant_id=tenant_id, bundle_id=bundle_id)
        deferral_omission = evaluate_permanent_orphan_omission_posture_v1(
            deferral_counts=deferral_counts
        )
        deferred_total = int(deferral_counts.get("deferred_total") or 0)
        if deferred_total:
            omission_classes["canonical_deferrals_active"] = deferred_total
        if drainable_routable_estimate:
            omission_classes["canonical_drainable_backlog"] = drainable_routable_estimate
    elif admin_fast and unmaterialized:
        omission_classes["canonical_backlog_admin_fast_estimate"] = unmaterialized

    degraded = len(failures)
    substrate_state = "critical" if raw_total > 0 and mat_total == 0 else (
        "degraded" if failures or unmaterialized > raw_total * 0.05 else "healthy"
    )
    replay_posture = "partial" if failures else ("stable" if mat_total else "unknown")

    return build_stage_envelope_v1(
        stage_id="canonical",
        label="Canonical",
        total_objects=raw_total,
        processed_count=mat_total,
        degraded_count=degraded,
        unresolved_count=unmaterialized,
        omitted_count=unsupported + parse_failed,
        intentionally_excluded_count=unsupported,
        replay_posture=replay_posture,
        substrate_state=substrate_state,
        drift_warnings=[f"{schema_drift} schema_drift case(s)"] if schema_drift else [],
        omission_classes=omission_classes,
        detail_route=f"/admin/tenants/{tenant_id}/cortex/canonical",
        metrics={
            "raw_count": raw_total,
            "canonicalized_count": mat_total,
            "raw_minus_mat_admin_gap": unmaterialized,
            "untreated_routable_estimate": untreated_routable_estimate,
            "drainable_routable_estimate": drainable_routable_estimate,
            "deferral_counts": deferral_counts,
            "operator_kpi_primary": "drainable_routable_estimate",
            "deferral_omission_posture": deferral_omission.get("posture"),
            "deferred_permanent_orphan": int(deferral_counts.get("deferred_permanent_orphan") or 0),
            "chase_zero_deferrals_forbidden": deferral_omission.get(
                "chase_zero_deferrals_forbidden"
            ),
            "unsupported_count": unsupported,
            "parse_failed_count": parse_failed,
            "schema_drift_count": schema_drift,
            "conversion_percent": pct(mat_total, raw_total if raw_total else 1),
        },
    )
