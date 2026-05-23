"""Substrate SQL metrics for continuity audit snapshot (C3 merge of prod_substrate_proof_queries)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.phase08_empty_scope_truth_gate import (
    count_retrieval_entries_in_published_epoch_v1,
)
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.cortex_tenant_convergence_lease import CortexTenantConvergenceLease
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)

SUBSTRATE_SQL_SNAPSHOT_SCHEMA_VERSION = 1
MAX_OBLIGATION_EPOCH_GAP_V1 = 2


def build_substrate_sql_snapshot_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Key prod SQL continuity metrics (merged from ``prod_substrate_proof_queries``)."""
    lease_row = session.get(CortexTenantConvergenceLease, tenant_id)
    lease: dict[str, Any] | None = None
    obligation_gap: int | None = None
    obligation_gap_ok: bool | None = None
    if lease_row is not None:
        obligation = int(lease_row.obligation_epoch or 0)
        target = int(lease_row.target_epoch or 0)
        obligation_gap = obligation - target
        obligation_gap_ok = obligation_gap <= MAX_OBLIGATION_EPOCH_GAP_V1
        lease = {
            "status": lease_row.status,
            "fsm_state": lease_row.fsm_state,
            "phase_cursor": lease_row.phase_cursor,
            "obligation_epoch": obligation,
            "target_epoch": target,
            "obligation_minus_target": obligation_gap,
            "obligation_epoch_gap_ok": obligation_gap_ok,
            "block_reason_code": lease_row.block_reason_code,
            "pipeline_run_id": str(lease_row.pipeline_run_id) if lease_row.pipeline_run_id else None,
        }

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
    org_entities_active = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(
                CortexOrgEntity.tenant_id == tenant_id,
                CortexOrgEntity.tombstoned_at.is_(None),
                CortexOrgEntity.lifecycle_state == "active",
            )
        )
        or 0
    )
    auth_links = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_authority == "authoritative",
            )
        )
        or 0
    )

    synthesis_jobs_by_status: dict[str, int] = {}
    for status, count in session.execute(
        select(CortexSynthesisJob.status, func.count())
        .where(CortexSynthesisJob.tenant_id == tenant_id)
        .group_by(CortexSynthesisJob.status)
    ).all():
        synthesis_jobs_by_status[str(status)] = int(count)

    artifacts_published = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisArtifact)
            .where(
                CortexSynthesisArtifact.tenant_id == tenant_id,
                CortexSynthesisArtifact.published.is_(True),
            )
        )
        or 0
    )
    artifacts_total = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisArtifact)
            .where(CortexSynthesisArtifact.tenant_id == tenant_id)
        )
        or 0
    )

    retrieval_epoch = count_retrieval_entries_in_published_epoch_v1(session, tenant_id=tenant_id)

    deferral_row = session.execute(
        text(
            """
            SELECT
              COUNT(*)::bigint AS total,
              COUNT(*) FILTER (WHERE COALESCE(detail_json->>'permanent_orphan','') = 'true')::bigint
                AS permanent_orphan,
              COUNT(*) FILTER (WHERE retry_ready_at > NOW())::bigint AS on_cooldown,
              COUNT(*) FILTER (
                WHERE retry_ready_at <= NOW()
                  AND COALESCE(detail_json->>'permanent_orphan','') != 'true'
              )::bigint AS retry_ready
            FROM cortex_canonical_materialization_deferrals
            WHERE tenant_id = :tenant_id
            """
        ),
        {"tenant_id": str(tenant_id)},
    ).mappings().first()

    phase_runs = [
        dict(row)
        for row in session.execute(
            text(
                """
                SELECT pr.phase_id, pr.status, pr.started_at, pr.completed_at,
                       LEFT(COALESCE(pr.error_detail, ''), 120) AS error_detail_preview
                FROM cortex_substrate_phase_runs pr
                JOIN cortex_substrate_pipeline_runs r ON r.id = pr.pipeline_run_id
                WHERE r.tenant_id = :tenant_id
                ORDER BY pr.started_at DESC NULLS LAST
                LIMIT 12
                """
            ),
            {"tenant_id": str(tenant_id)},
        ).mappings()
    ]

    return {
        "surface_kind": "continuity_substrate_sql_snapshot",
        "substrate_sql_schema_version": SUBSTRATE_SQL_SNAPSHOT_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "lease": lease,
        "obligation_epoch_gap": obligation_gap,
        "obligation_epoch_gap_ok": obligation_gap_ok,
        "raw_total": raw_total,
        "mat_total": mat_total,
        "raw_minus_mat_admin_gap": raw_total - mat_total,
        "org_entities_active": org_entities_active,
        "auth_links": auth_links,
        "synthesis_jobs_by_status": synthesis_jobs_by_status,
        "artifacts_published": artifacts_published,
        "artifacts_total": artifacts_total,
        "retrieval_entries_in_published_epoch": retrieval_epoch.get("retrieval_entries_in_epoch"),
        "published_index_epoch": retrieval_epoch.get("published_index_epoch"),
        "deferral_totals": dict(deferral_row) if deferral_row else None,
        "recent_phase_runs": phase_runs,
    }
