"""Phase D step D1 — operator primary KPI on pipeline overview (drainable + islands)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.execution_island_registry import (
    build_island_registry_inspect_v1,
    is_execution_island_registry_enabled_v1,
    list_execution_island_registry_v1,
)
from vector.domains.cortex.canonical.permanent_orphan_omission_doctrine import (
    build_deferral_omission_operator_block_v1,
)
from vector.domains.cortex.pipeline.canonical_operator_metrics import (
    _canonical_operator_backlog_count,
    snapshot_canonical_operator_metrics_v1,
)
from vector.settings import Settings, get_settings

P0_D1_STEP: str = "step_d1_admin_operator_primary_kpi"
PHASE_D1_OPERATOR_KPI_SCHEMA_VERSION: int = 1
_ADMIN_ISLAND_LIST_CAP_V1 = 32


def is_admin_primary_kpi_drainable_enabled_v1(*, settings: Settings | None = None) -> bool:
    if settings is None:
        settings = get_settings()
    return bool(getattr(settings, "cortex_admin_primary_kpi_drainable", True))


def build_operator_primary_kpi_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    overview_slice: bool = False,
    precomputed_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Top-level admin KPI block for pipeline overview slices."""
    settings = settings or get_settings()

    metrics = precomputed_metrics or snapshot_canonical_operator_metrics_v1(
        session, tenant_id=tenant_id
    )
    if overview_slice:
        return {
            "surface_kind": "operator_primary_kpi",
            "schema_version": PHASE_D1_OPERATOR_KPI_SCHEMA_VERSION,
            "semantic_primary_active": True,
            "hide_from_overview": True,
            "primary_metric_key": "unique_auth_pairs",
            "primary_metric_value": 0,
            "drainable_routable_estimate": int(metrics.get("drainable_routable_estimate") or 0),
            "untreated_routable_estimate": int(metrics.get("untreated_routable_estimate") or 0),
            "raw_minus_mat_admin_gap": int(metrics.get("raw_minus_mat_admin_gap") or 0),
            "deferral_counts": dict(metrics.get("deferral_counts") or {}),
            "operator_kpi_primary": "semantic_readiness_panel",
            "canonical_backlog_count": _canonical_operator_backlog_count(metrics),
            "deferral_omission": build_deferral_omission_operator_block_v1(
                session,
                tenant_id=tenant_id,
                deferral_counts=dict(metrics.get("deferral_counts") or {}),
            ),
        }

    from vector.domains.cortex.pipeline.pipeline_admin_semantic_readiness import (
        build_semantic_readiness_admin_v1,
    )

    semantic = build_semantic_readiness_admin_v1(session, settings, tenant_id=tenant_id)
    graph = dict(semantic.get("graph_truth") or {})
    retrieval = dict(semantic.get("retrieval") or {})
    synthesis = dict(semantic.get("synthesis") or {})
    primary_key = "unique_auth_pairs"
    primary_value = int(graph.get("unique_auth_pairs") or 0)
    registry_enabled = is_execution_island_registry_enabled_v1()
    islands_raw = list_execution_island_registry_v1(session, tenant_id=tenant_id)
    islands = [
        {
            "island_scope_id": row["island_scope_id"],
            "entity_count": row["entity_count"],
            "authoritative_edge_count": row["authoritative_edge_count"],
            "last_retrieval_epoch": row.get("last_retrieval_epoch"),
            "last_walk_at": row.get("last_walk_at"),
            "registry_snapshot_at": row.get("registry_snapshot_at"),
            "live_authoritative_edge_count": row.get("authoritative_edge_count"),
        }
        for row in islands_raw[:_ADMIN_ISLAND_LIST_CAP_V1]
    ]
    registry_inspect = build_island_registry_inspect_v1(session, tenant_id=tenant_id, sync=False)
    return {
        "surface_kind": "operator_primary_kpi",
        "schema_version": PHASE_D1_OPERATOR_KPI_SCHEMA_VERSION,
        "semantic_primary_active": True,
        "hide_from_overview": True,
        "primary_metric_key": primary_key,
        "primary_metric_value": primary_value,
        "semantic_operator_panel": semantic.get("semantic_operator_panel"),
        "dup_factor": graph.get("dup_factor"),
        "promotion_rule_count": graph.get("promotion_rule_count"),
        "retrieval_org_link_pct": retrieval.get("org_link_pct"),
        "retrieval_execution_index_pct": retrieval.get("execution_index_pct"),
        "published_claims_7d": synthesis.get("published_claims_7d"),
        "retrieval_freshness_minutes": retrieval.get("freshness_minutes"),
        "drainable_routable_estimate": int(metrics.get("drainable_routable_estimate") or 0),
        "untreated_routable_estimate": int(metrics.get("untreated_routable_estimate") or 0),
        "raw_minus_mat_admin_gap": int(metrics.get("raw_minus_mat_admin_gap") or 0),
        "raw_minus_mat_banner_deprecated": True,
        "diagnostic_only": True,
        "deferral_counts": dict(metrics.get("deferral_counts") or {}),
        "operator_kpi_primary": "semantic_readiness_panel",
        "canonical_backlog_count": _canonical_operator_backlog_count(metrics),
        "execution_island_registry_enabled": registry_enabled,
        "execution_island_count": len(islands_raw),
        "execution_islands": islands,
        "island_registry_inspect": {
            "surface_kind": registry_inspect.get("surface_kind"),
            "island_count": registry_inspect.get("island_count"),
            "traversal_propagation": registry_inspect.get("traversal_propagation"),
            "registry_snapshot_at": registry_inspect.get("registry_snapshot_at"),
        },
        "deferral_omission": build_deferral_omission_operator_block_v1(
            session,
            tenant_id=tenant_id,
            deferral_counts=dict(metrics.get("deferral_counts") or {}),
        ),
    }
