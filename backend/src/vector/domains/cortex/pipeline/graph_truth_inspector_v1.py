"""Graph truth inspector — evidence-backed operator surface (Phase G1).

Wraps the CLI audit snapshot with edge-type distribution and inflation signals
for the admin graph tab redesign.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.semantic_readiness_v1 import (
    build_graph_truth_audit_snapshot_v1,
)
from vector.domains.cortex.substrate_pipeline.graph_truth_metrics_v1 import (
    snapshot_promotion_diversity_observability_v1,
)

GRAPH_TRUTH_INSPECTOR_SCHEMA_VERSION = 1
_TOPOLOGY_MIRROR_LINK_TYPE = "org.persona_belongs_to_handle"


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def _query_edge_type_distribution_v1(session: Session, *, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    tid = str(tenant_id)
    rows = [
        dict(r)
        for r in session.execute(
            text(
                """
                SELECT link_type,
                       COUNT(*)::bigint AS auth_edge_rows,
                       COUNT(DISTINCT (source_entity_id, target_entity_id))::bigint AS unique_pairs,
                       COUNT(DISTINCT rule_id)::bigint AS rule_count
                FROM cortex_org_links
                WHERE tenant_id = :tenant
                  AND link_authority = 'authoritative'
                  AND revoked_at IS NULL
                GROUP BY 1
                ORDER BY auth_edge_rows DESC, unique_pairs DESC, link_type ASC
                """
            ),
            {"tenant": tid},
        ).mappings()
    ]
    total_rows = sum(_to_int(r["auth_edge_rows"]) for r in rows)
    total_unique = sum(_to_int(r["unique_pairs"]) for r in rows)
    out: list[dict[str, Any]] = []
    for r in rows:
        auth_rows = _to_int(r["auth_edge_rows"])
        unique_pairs = _to_int(r["unique_pairs"])
        dup = round(auth_rows / unique_pairs, 3) if unique_pairs > 0 else None
        out.append(
            {
                "link_type": str(r["link_type"] or "(null)"),
                "auth_edge_rows": auth_rows,
                "unique_pairs": unique_pairs,
                "dup_factor": dup,
                "rule_count": _to_int(r["rule_count"]),
                "pct_of_auth_rows": round(100.0 * auth_rows / total_rows, 2) if total_rows else 0.0,
                "pct_of_unique_pairs": round(100.0 * unique_pairs / total_unique, 2) if total_unique else 0.0,
                "is_topology_mirror": str(r["link_type"]) == _TOPOLOGY_MIRROR_LINK_TYPE,
            }
        )
    return out


def build_graph_truth_inspector_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    include_connected_components: bool = False,
) -> dict[str, Any]:
    """Operator graph-truth inspector payload for admin graph tab (Phase G1)."""
    audit = build_graph_truth_audit_snapshot_v1(
        session,
        tenant_id=tenant_id,
        include_connected_components=include_connected_components,
    )
    graph_truth = dict(audit.get("graph_truth") or {})
    edge_types = _query_edge_type_distribution_v1(session, tenant_id=tenant_id)

    mirror = next((e for e in edge_types if e["link_type"] == _TOPOLOGY_MIRROR_LINK_TYPE), None)
    mirror_row_pct = float(mirror["pct_of_auth_rows"]) if mirror else 0.0
    mirror_unique_pct = float(mirror["pct_of_unique_pairs"]) if mirror else 0.0

    execution_link_types = [
        e for e in edge_types if not e["is_topology_mirror"] and e["unique_pairs"] > 0
    ]
    execution_unique_pairs = sum(int(e["unique_pairs"]) for e in execution_link_types)
    total_unique = int(graph_truth.get("unique_auth_pairs") or 0)
    cross_system_pct = (
        round(100.0 * execution_unique_pairs / total_unique, 2) if total_unique > 0 else 0.0
    )
    promotion_diversity = snapshot_promotion_diversity_observability_v1(session, tenant_id=tenant_id)

    return {
        **audit,
        "surface_kind": "graph_truth_inspector",
        "inspector_schema_version": GRAPH_TRUTH_INSPECTOR_SCHEMA_VERSION,
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "edge_type_distribution": edge_types,
        "inflation_signals": {
            "topology_mirror_link_type": _TOPOLOGY_MIRROR_LINK_TYPE,
            "topology_mirror_row_pct": mirror_row_pct,
            "topology_mirror_unique_pair_pct": mirror_unique_pct,
            "topology_mirror_dominates": mirror_row_pct >= 50.0,
            "dup_factor": graph_truth.get("dup_factor"),
            "dup_factor_severity": graph_truth.get("dup_factor_severity"),
            "unpromoted_candidates": audit.get("unpromoted_candidates"),
            "candidate_total": dict(audit.get("candidates") or {}).get("total"),
        },
        "continuity_signals": {
            "cross_system_unique_pair_pct": cross_system_pct,
            "execution_link_type_count": len(execution_link_types),
            "entities_in_auth_graph_pct": graph_truth.get("entities_in_auth_graph_pct"),
            "entities_isolated": graph_truth.get("entities_isolated"),
            "promotion_rule_count": graph_truth.get("promotion_rule_count"),
            "promotion_diversity": promotion_diversity,
        },
        "product_laws": {
            "retrieval_org_link_pct_max": audit.get("thresholds", {}).get("retrieval_org_link_pct_green_max"),
            "retrieval_execution_index_pct_min": audit.get("thresholds", {}).get(
                "retrieval_execution_index_pct_green_min"
            ),
            "dup_factor_green_max": audit.get("thresholds", {}).get("dup_factor_green_max"),
        },
    }
