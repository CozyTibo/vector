"""Lightweight identity continuity health semantics (operator truth, no new runtime)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.identity_onboarding_seeds import load_onboarding_continuity_seeds_v1
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

IDENTITY_CONTINUITY_HEALTH_SCHEMA_VERSION = 1

ACTOR_GAP_TAXONOMY: tuple[str, ...] = (
    "unresolved_actor_no_primitives",
    "github_login_without_email",
    "notion_user_id_missing_on_pages",
    "canonical_backlog_limits_primitive_extraction",
    "missing_topology_parent_not_identity",
    "unsupported_provider_identity_shape",
    "external_collaborator_likely",
    "deleted_upstream_user_unknown",
)


def build_identity_continuity_gap_reasons_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    anchors_scanned: int,
    primitive_metrics: dict[str, Any],
    github_email_metrics: dict[str, Any],
    candidate_row_count: int,
    anchors_rule_eligible: int,
) -> list[dict[str, Any]]:
    """Explain weak continuity without prescribing new orchestration."""
    reasons: list[dict[str, Any]] = []
    kind_counts = dict(primitive_metrics.get("identity_projection_kind_counts") or {})
    zero_primitives = int(primitive_metrics.get("anchors_with_zero_extracted_primitives") or 0)

    if zero_primitives > 0:
        reasons.append(
            {
                "code": "unresolved_actor_no_primitives",
                "severity": "warn",
                "detail": f"{zero_primitives} anchors produced zero identity primitives from raw evidence.",
            }
        )

    login_no_email = int(github_email_metrics.get("github_login_without_email_anchor_count") or 0)
    if login_no_email > 0:
        reasons.append(
            {
                "code": "github_login_without_email",
                "severity": "info",
                "detail": (
                    f"{login_no_email} GitHub anchors have login primitives but no explicit email "
                    "on the same row (common when GitHub withholds email)."
                ),
            }
        )

    notion_primitives = int(kind_counts.get("notion_user", 0))
    notion_raw = int(
        db.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.connector == "notion",
                RawIngestionRecord.resource_type.in_(("notion.page", "notion.database_row")),
            )
        )
        or 0
    )
    if notion_raw > 0 and notion_primitives < max(1, notion_raw // 10):
        reasons.append(
            {
                "code": "notion_user_id_missing_on_pages",
                "severity": "warn",
                "detail": (
                    "Notion content rows exist but few notion_user primitives — "
                    "created_by/last_edited_by may be absent or not yet materialized."
                ),
            }
        )

    raw_total = int(
        db.scalar(
            select(func.count()).select_from(RawIngestionRecord).where(RawIngestionRecord.tenant_id == tenant_id)
        )
        or 0
    )
    mat_total = int(
        db.scalar(
            select(func.count())
            .select_from(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        )
        or 0
    )
    untreated = max(0, raw_total - mat_total)
    if untreated > raw_total * 0.05 and anchors_scanned < raw_total // 2:
        reasons.append(
            {
                "code": "canonical_backlog_limits_primitive_extraction",
                "severity": "warn",
                "detail": (
                    f"~{untreated} raw rows lack canonical materialization; identity anchors "
                    "only exist after materialization."
                ),
            }
        )

    if anchors_scanned > 0 and candidate_row_count == 0 and anchors_rule_eligible == 0:
        reasons.append(
            {
                "code": "join_buckets_singleton",
                "severity": "info",
                "detail": (
                    "Primitives exist but no cross-entity continuity candidate edges yet "
                    "(singleton join buckets or cap reached)."
                ),
            }
        )

    return reasons


def build_identity_continuity_health_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    anchor_scan_limit: int = 50_000,
) -> dict[str, Any]:
    """Compact operator health snapshot built from existing deterministic surfaces."""
    from vector.domains.cortex.identity.continuity_evidence_inspector import (
        build_continuity_evidence_inspection,
    )

    inspection = build_continuity_evidence_inspection(
        db,
        tenant_id=tenant_id,
        anchor_scan_limit=anchor_scan_limit,
        sample_limit=10,
        fixture_survival_sample_limit=5,
    )
    onboarding = load_onboarding_continuity_seeds_v1(db, tenant_id=tenant_id)

    anchor_count = int(
        db.scalar(
            select(func.count())
            .select_from(CortexCanonicalIdentityAnchor)
            .where(CortexCanonicalIdentityAnchor.tenant_id == tenant_id)
        )
        or 0
    )

    return {
        "identity_continuity_health_schema_version": IDENTITY_CONTINUITY_HEALTH_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "anchor_count": anchor_count,
        "identity_primitive_projection_metrics": inspection.get("identity_primitive_projection_metrics"),
        "github_email_extraction_metrics": inspection.get("github_email_extraction_metrics"),
        "continuity_gap_reasons": inspection.get("continuity_gap_reasons"),
        "continuity_join_reason_catalog": inspection.get("continuity_join_reason_catalog"),
        "current_engine_candidate_row_count": inspection.get("current_engine_candidate_row_count"),
        "substrate_counters": inspection.get("substrate_counters"),
        "onboarding_continuity_seeds": onboarding,
        "actor_gap_taxonomy": list(ACTOR_GAP_TAXONOMY),
        "notes": [
            "Identity remains execution-derived; onboarding seeds are hints only.",
            "Use debug-anchor-evidence for sampled row-level join-key traces.",
        ],
    }
