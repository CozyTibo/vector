"""Wave S0 — semantic readiness / graph truth metrics (retrieval-first product substrate).

Operator and audit surfaces must use **unique auth pairs** and **retrieval mix**, not raw link row counts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    list_graph_connected_components_v1,
)

SEMANTIC_READINESS_SCHEMA_VERSION = 1
GRAPH_TRUTH_AUDIT_SCHEMA_VERSION = 1

# Wave S0 green thresholds (semantic phase plan).
DUP_FACTOR_GREEN_MAX = 1.05
DUP_FACTOR_WARN_MIN = 1.1
RETRIEVAL_ORG_LINK_PCT_GREEN_MAX = 30.0
RETRIEVAL_EXECUTION_PCT_GREEN_MIN = 60.0
PROMOTION_RULE_COUNT_GREEN_MIN = 3
ANCHORS_MISSING_ENTITY_PCT_GREEN_MAX = 50.0
CANDIDATE_INFLATION_RATIO_GREEN_MAX = 3.0

_EXECUTION_INDEX_KINDS = frozenset({"materialization", "walk", "causal_chain", "causal_edge"})


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value)
    return int(value)


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _dup_factor(*, auth_edge_rows: int, unique_auth_pairs: int) -> float | None:
    if unique_auth_pairs <= 0:
        return None
    return round(auth_edge_rows / unique_auth_pairs, 3)


def _dup_severity(dup_factor: float | None) -> str:
    if dup_factor is None:
        return "unknown"
    if dup_factor <= DUP_FACTOR_GREEN_MAX:
        return "ok"
    if dup_factor >= DUP_FACTOR_WARN_MIN:
        return "bad"
    return "warn"


def _query_graph_truth_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    include_connected_components: bool = False,
) -> dict[str, Any]:
    from vector.domains.cortex.substrate_pipeline.graph_truth_metrics_v1 import (
        snapshot_authoritative_link_topology_v1,
    )

    tid = str(tenant_id)
    topo = snapshot_authoritative_link_topology_v1(session, tenant_id=tenant_id)
    active_entities = _to_int(
        session.execute(
            text(
                """
                SELECT COUNT(*)::bigint AS n FROM cortex_org_entities
                WHERE tenant_id = :tenant AND tombstoned_at IS NULL AND lifecycle_state = 'active'
                """
            ),
            {"tenant": tid},
        ).scalar()
    )
    auth_edge_rows = _to_int(topo.get("auth_edge_rows"))
    unique_auth_pairs = _to_int(topo.get("unique_auth_pairs"))
    dup = topo.get("dup_factor")
    if dup is not None:
        dup = float(dup)

    incident = session.execute(
        text(
            """
            WITH incident AS (
              SELECT source_entity_id AS eid FROM cortex_org_links
              WHERE tenant_id = :tenant AND link_authority = 'authoritative' AND revoked_at IS NULL
              UNION
              SELECT target_entity_id FROM cortex_org_links
              WHERE tenant_id = :tenant AND link_authority = 'authoritative' AND revoked_at IS NULL
            )
            SELECT COUNT(DISTINCT eid)::bigint AS in_graph
            FROM incident
            """
        ),
        {"tenant": tid},
    ).mappings().first()
    in_graph = _to_int(incident["in_graph"]) if incident else 0
    isolated = max(0, active_entities - in_graph)
    in_graph_pct = round(100.0 * in_graph / active_entities, 2) if active_entities else 0.0

    promotions = [
        {
            "rule_id": str(r["rule_id"] or "(null)"),
            "auth_edge_rows": _to_int(r["auth_edge_rows"]),
            "unique_pairs": _to_int(r["unique_pairs"]),
        }
        for r in session.execute(
            text(
                """
                SELECT COALESCE(rule_id, '(null)') AS rule_id,
                       COUNT(*)::bigint AS auth_edge_rows,
                       COUNT(DISTINCT (source_entity_id, target_entity_id))::bigint AS unique_pairs
                FROM cortex_org_links
                WHERE tenant_id = :tenant AND link_authority = 'authoritative' AND revoked_at IS NULL
                GROUP BY 1 ORDER BY unique_pairs DESC, auth_edge_rows DESC
                """
            ),
            {"tenant": tid},
        ).mappings()
    ]
    rules_with_edges = sum(1 for p in promotions if p["unique_pairs"] > 0)

    components_summary: dict[str, Any] = {}
    if include_connected_components:
        try:
            components = list_graph_connected_components_v1(session, tenant_id=tenant_id)
            sizes = sorted((len(c) for c in components), reverse=True)
            components_summary = {
                "component_count": len(sizes),
                "largest_component_size": sizes[0] if sizes else 0,
                "component_sizes_top_10": sizes[:10],
                "components_size_ge_2": sum(1 for s in sizes if s >= 2),
            }
        except Exception as exc:  # noqa: BLE001
            components_summary = {"error": str(exc)[:300]}

    return {
        "active_entities": active_entities,
        "entities_in_auth_graph": in_graph,
        "entities_isolated": isolated,
        "entities_in_auth_graph_pct": in_graph_pct,
        "auth_edge_rows": auth_edge_rows,
        "auth_edge_rows_deprecated_primary": True,
        "unique_auth_pairs": unique_auth_pairs,
        "dup_factor": dup,
        "dup_factor_severity": _dup_severity(dup),
        "promotion_rule_count": rules_with_edges,
        "promotions_by_rule_id": promotions,
        "connected_components": components_summary,
        "primary_metric_key": "unique_auth_pairs",
    }


def _retrieval_freshness_green_minutes_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_retrieval_freshness_green_minutes))
    except Exception:  # noqa: BLE001
        return 120


def _freshness_severity(freshness_minutes: float | None) -> str:
    if freshness_minutes is None:
        return "unknown"
    if freshness_minutes <= _retrieval_freshness_green_minutes_v1():
        return "ok"
    return "bad"


def _query_retrieval_product_v1(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    tid = str(tenant_id)
    published = session.execute(
        text(
            """
            SELECT index_epoch, published_at, entry_count
            FROM cortex_retrieval_index_epochs
            WHERE tenant_id = :tenant AND published_at IS NOT NULL
            ORDER BY published_at DESC NULLS LAST
            LIMIT 1
            """
        ),
        {"tenant": tid},
    ).mappings().first()

    if not published:
        return {
            "published_index_epoch": None,
            "published_at": None,
            "entry_count": 0,
            "index_kind_counts": [],
            "org_link_pct": None,
            "execution_index_pct": None,
            "freshness_minutes": None,
            "product_substrate_note": "retrieval_epochs_are_primary_product_surface",
        }

    epoch = str(published["index_epoch"])
    mix_rows = [
        dict(r)
        for r in session.execute(
            text(
                """
                SELECT index_kind, COUNT(*)::bigint AS n
                FROM cortex_retrieval_index_entries
                WHERE tenant_id = :tenant AND index_epoch = :epoch
                GROUP BY 1 ORDER BY n DESC
                """
            ),
            {"tenant": tid, "epoch": epoch},
        ).mappings()
    ]
    total = sum(_to_int(r["n"]) for r in mix_rows)
    org_link = sum(_to_int(r["n"]) for r in mix_rows if str(r["index_kind"]) == "org_link")
    execution_n = sum(
        _to_int(r["n"]) for r in mix_rows if str(r["index_kind"]) in _EXECUTION_INDEX_KINDS
    )
    org_link_pct = round(100.0 * org_link / total, 2) if total else None
    execution_pct = round(100.0 * execution_n / total, 2) if total else None

    freshness = session.execute(
        text(
            """
            SELECT EXTRACT(EPOCH FROM (NOW() - MAX(created_at))) / 60.0 AS freshness_minutes
            FROM cortex_retrieval_index_entries
            WHERE tenant_id = :tenant
            """
        ),
        {"tenant": tid},
    ).mappings().first()
    freshness_minutes = (
        round(_to_float(freshness["freshness_minutes"]), 1) if freshness else None
    )

    return {
        "published_index_epoch": epoch,
        "published_at": published.get("published_at"),
        "entry_count": _to_int(published.get("entry_count")),
        "index_kind_counts": [
            {"index_kind": str(r["index_kind"]), "count": _to_int(r["n"])} for r in mix_rows
        ],
        "org_link_pct": org_link_pct,
        "execution_index_pct": execution_pct,
        "freshness_minutes": freshness_minutes,
        "org_link_pct_severity": (
            "ok"
            if org_link_pct is not None and org_link_pct <= RETRIEVAL_ORG_LINK_PCT_GREEN_MAX
            else "bad"
            if org_link_pct is not None
            else "unknown"
        ),
        "execution_index_pct_severity": (
            "ok"
            if execution_pct is not None and execution_pct >= RETRIEVAL_EXECUTION_PCT_GREEN_MIN
            else "bad"
            if execution_pct is not None
            else "unknown"
        ),
        "freshness_minutes_severity": _freshness_severity(freshness_minutes),
        "freshness_green_minutes": _retrieval_freshness_green_minutes_v1(),
    }


def _candidate_inflation_severity(ratio: float | None) -> str:
    if ratio is None:
        return "unknown"
    if ratio <= CANDIDATE_INFLATION_RATIO_GREEN_MAX:
        return "ok"
    return "bad"


def _anchors_missing_severity(pct: float | None) -> str:
    if pct is None:
        return "unknown"
    if pct <= ANCHORS_MISSING_ENTITY_PCT_GREEN_MAX:
        return "ok"
    if pct >= 80.0:
        return "bad"
    return "warn"


def _query_identity_continuity_v1(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    from vector.domains.cortex.identity.identity_anchor_boundary_v1 import (
        snapshot_anchor_entity_boundary_v1,
    )
    from vector.domains.cortex.identity.identity_continuity_promotion_v1 import (
        count_promotable_link_candidates_by_rule_v1,
    )
    from vector.domains.cortex.substrate_pipeline.graph_truth_metrics_v1 import (
        snapshot_promotion_diversity_observability_v1,
    )

    tid = str(tenant_id)
    boundary = snapshot_anchor_entity_boundary_v1(session, tenant_id=tenant_id)
    promotion_diversity = snapshot_promotion_diversity_observability_v1(session, tenant_id=tenant_id)
    cand = session.execute(
        text(
            """
            SELECT COUNT(*)::bigint AS total,
                   COUNT(DISTINCT (source_entity_id, target_entity_id, link_type))::bigint
                     AS distinct_pairs,
                   COUNT(DISTINCT rule_id)::bigint AS distinct_rules
            FROM cortex_org_link_candidates WHERE tenant_id = :tenant
            """
        ),
        {"tenant": tid},
    ).mappings().first()
    candidate_rows = _to_int(cand["total"]) if cand else 0
    distinct_pairs = _to_int(cand["distinct_pairs"]) if cand else 0
    inflation: float | None = None
    if distinct_pairs > 0:
        inflation = round(candidate_rows / distinct_pairs, 3)
    return {
        "anchor_boundary": boundary,
        "candidate_rows": candidate_rows,
        "distinct_candidate_pairs": distinct_pairs,
        "candidate_inflation_ratio": inflation,
        "candidate_inflation_severity": _candidate_inflation_severity(inflation),
        "anchors_missing_org_entity_pct": boundary.get("anchors_missing_org_entity_pct"),
        "anchors_missing_severity": _anchors_missing_severity(
            boundary.get("anchors_missing_org_entity_pct")
            if isinstance(boundary.get("anchors_missing_org_entity_pct"), (int, float))
            else None
        ),
        "promotable_by_rule_id": count_promotable_link_candidates_by_rule_v1(session, tenant_id=tenant_id),
        "promotion_diversity": promotion_diversity,
        "promotion_rule_count_green_min": PROMOTION_RULE_COUNT_GREEN_MIN,
        "second_link_type_policy": "deferred_until_prod_evidence_ge_100_edges",
        "primary_metric_keys": [
            "promotable_by_rule_id",
            "promotion_diversity.promotion_diversity_severity",
            "anchors_missing_org_entity_pct",
            "candidate_inflation_ratio",
        ],
    }


def _query_synthesis_truth_v1(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    tid = str(tenant_id)
    jobs = [
        {"status": str(r["status"]), "count": _to_int(r["n"])}
        for r in session.execute(
            text(
                """
                SELECT status, COUNT(*)::bigint AS n
                FROM cortex_synthesis_jobs WHERE tenant_id = :tenant
                GROUP BY 1 ORDER BY n DESC
                """
            ),
            {"tenant": tid},
        ).mappings()
    ]
    artifacts = session.execute(
        text(
            """
            SELECT
              COUNT(*)::bigint AS total,
              COUNT(*) FILTER (WHERE published IS TRUE)::bigint AS published,
              COUNT(*) FILTER (
                WHERE COALESCE(jsonb_array_length(body_json->'claims'), 0) > 0
              )::bigint AS with_claims
            FROM cortex_synthesis_artifacts
            WHERE tenant_id = :tenant
            """
        ),
        {"tenant": tid},
    ).mappings().first()
    published_7d = session.execute(
        text(
            """
            SELECT COUNT(*)::bigint AS n
            FROM cortex_synthesis_artifacts
            WHERE tenant_id = :tenant
              AND published IS TRUE
              AND published_at >= NOW() - INTERVAL '7 days'
              AND COALESCE(jsonb_array_length(body_json->'claims'), 0) > 0
            """
        ),
        {"tenant": tid},
    ).scalar()
    published_claims_7d = _to_int(published_7d)
    return {
        "jobs_by_status": jobs,
        "artifacts_total": _to_int(artifacts["total"]) if artifacts else 0,
        "artifacts_published": _to_int(artifacts["published"]) if artifacts else 0,
        "artifacts_with_claims": _to_int(artifacts["with_claims"]) if artifacts else 0,
        "published_claims_7d": published_claims_7d,
        "published_claims_7d_severity": (
            "ok" if published_claims_7d >= 1 else ("bad" if _to_int(artifacts["published"]) else "unknown")
        ),
        "published_claims_7d_green_min": 1,
        "fail_loud_expected_when_retrieval_weak": True,
    }


def build_semantic_operator_panel_v1(
    *,
    graph: dict[str, Any],
    retrieval: dict[str, Any],
    synthesis: dict[str, Any],
) -> list[dict[str, Any]]:
    """Wave S5 step 23 — six operator metrics (phase plan §9)."""
    return [
        {
            "key": "unique_auth_pairs",
            "label": "Unique auth pairs",
            "value": graph.get("unique_auth_pairs"),
            "severity": graph.get("dup_factor_severity"),
            "green_rule": "dup_factor ≤ 1.05; pairs ↑ week-over-week",
        },
        {
            "key": "promotion_rule_count",
            "label": "Promotion rules (with edges)",
            "value": graph.get("promotion_rule_count"),
            "severity": "ok" if int(graph.get("promotion_rule_count") or 0) >= PROMOTION_RULE_COUNT_GREEN_MIN else "bad",
            "green_rule": f"≥ {PROMOTION_RULE_COUNT_GREEN_MIN}",
        },
        {
            "key": "retrieval_org_link_pct",
            "label": "Retrieval org_link %",
            "value": retrieval.get("org_link_pct"),
            "severity": retrieval.get("org_link_pct_severity"),
            "green_rule": f"≤ {RETRIEVAL_ORG_LINK_PCT_GREEN_MAX}%",
        },
        {
            "key": "retrieval_execution_index_pct",
            "label": "Retrieval execution index %",
            "value": retrieval.get("execution_index_pct"),
            "severity": retrieval.get("execution_index_pct_severity"),
            "green_rule": f"≥ {RETRIEVAL_EXECUTION_PCT_GREEN_MIN}%",
        },
        {
            "key": "synthesis_published_claims_7d",
            "label": "Published claims (7d)",
            "value": synthesis.get("published_claims_7d"),
            "severity": synthesis.get("published_claims_7d_severity"),
            "green_rule": "≥ 1 useful artifact / 7d",
        },
        {
            "key": "retrieval_freshness_minutes",
            "label": "Retrieval freshness (min)",
            "value": retrieval.get("freshness_minutes"),
            "severity": retrieval.get("freshness_minutes_severity"),
            "green_rule": f"< {_retrieval_freshness_green_minutes_v1()} when ingest active",
        },
    ]


def build_semantic_readiness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    include_connected_components: bool = False,
) -> dict[str, Any]:
    """Lean semantic readiness payload for admin API and ops panels."""
    graph = _query_graph_truth_v1(
        session, tenant_id=tenant_id, include_connected_components=include_connected_components
    )
    identity = _query_identity_continuity_v1(session, tenant_id=tenant_id)
    retrieval = _query_retrieval_product_v1(session, tenant_id=tenant_id)
    synthesis = _query_synthesis_truth_v1(session, tenant_id=tenant_id)
    operator_panel = build_semantic_operator_panel_v1(
        graph=graph,
        retrieval=retrieval,
        synthesis=synthesis,
    )
    return {
        "surface_kind": "semantic_readiness",
        "schema_version": SEMANTIC_READINESS_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "product_substrate": "retrieval",
        "graph_truth": graph,
        "identity_continuity": identity,
        "retrieval": retrieval,
        "synthesis": synthesis,
        "semantic_operator_panel": operator_panel,
        "thresholds": {
            "dup_factor_green_max": DUP_FACTOR_GREEN_MAX,
            "promotion_rule_count_green_min": PROMOTION_RULE_COUNT_GREEN_MIN,
            "anchors_missing_entity_pct_green_max": ANCHORS_MISSING_ENTITY_PCT_GREEN_MAX,
            "candidate_inflation_ratio_green_max": CANDIDATE_INFLATION_RATIO_GREEN_MAX,
            "retrieval_org_link_pct_green_max": RETRIEVAL_ORG_LINK_PCT_GREEN_MAX,
            "retrieval_execution_index_pct_green_min": RETRIEVAL_EXECUTION_PCT_GREEN_MIN,
            "retrieval_freshness_green_minutes": _retrieval_freshness_green_minutes_v1(),
        },
    }


def build_graph_truth_audit_snapshot_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    include_connected_components: bool = False,
) -> dict[str, Any]:
    """Full graph-truth audit JSON (operators: ``graph_truth_audit_snapshot.py``)."""
    core = build_semantic_readiness_v1(
        session,
        tenant_id=tenant_id,
        include_connected_components=include_connected_components,
    )
    tid = str(tenant_id)
    candidates = session.execute(
        text(
            """
            SELECT COUNT(*)::bigint AS total,
                   COUNT(DISTINCT (source_entity_id, target_entity_id, link_type))::bigint AS distinct_pairs
            FROM cortex_org_link_candidates WHERE tenant_id = :tenant
            """
        ),
        {"tenant": tid},
    ).mappings().first()
    unpromoted_count = 0
    try:
        unpromoted = session.execute(
            text(
                """
                SELECT COUNT(*)::bigint AS n
                FROM cortex_org_link_candidates c
                WHERE c.tenant_id = :tenant
                  AND NOT EXISTS (
                    SELECT 1 FROM cortex_org_links l
                    WHERE l.tenant_id = c.tenant_id AND l.promoted_from_candidate_id = c.id
                  )
                """
            ),
            {"tenant": tid},
        ).mappings().first()
        unpromoted_count = _to_int(unpromoted["n"]) if unpromoted else 0
    except Exception:  # noqa: BLE001
        unpromoted_count = 0
    return {
        **core,
        "surface_kind": "graph_truth_audit_snapshot",
        "audit_schema_version": GRAPH_TRUTH_AUDIT_SCHEMA_VERSION,
        "candidates": {
            "total": _to_int(candidates["total"]) if candidates else 0,
            "distinct_pairs": _to_int(candidates["distinct_pairs"]) if candidates else 0,
        },
        "unpromoted_candidates": unpromoted_count,
        "repro_command": "python backend/scripts/graph_truth_audit_snapshot.py --tenant <id> --json",
        "companion_command": (
            "python backend/scripts/continuity_audit_snapshot.py --tenant <id> --json"
        ),
    }


def format_semantic_readiness_text_v1(snapshot: dict[str, Any]) -> str:
    """Human-readable summary for CLI."""
    g = dict(snapshot.get("graph_truth") or {})
    ic = dict(snapshot.get("identity_continuity") or {})
    r = dict(snapshot.get("retrieval") or {})
    s = dict(snapshot.get("synthesis") or {})
    lines = [
        f"Semantic readiness (tenant {snapshot.get('tenant_id')})",
        f"  Product substrate: {snapshot.get('product_substrate')}",
        f"  Unique auth pairs: {g.get('unique_auth_pairs')} (primary)",
        f"  Auth edge rows: {g.get('auth_edge_rows')} (dup_factor={g.get('dup_factor')}, "
        f"severity={g.get('dup_factor_severity')})",
        f"  Promotion rules with edges: {g.get('promotion_rule_count')}",
        f"  Anchors missing org entity: {ic.get('anchors_missing_org_entity_pct')}% "
        f"(severity={ic.get('anchors_missing_severity')})",
        f"  Candidate inflation ratio: {ic.get('candidate_inflation_ratio')} "
        f"(severity={ic.get('candidate_inflation_severity')})",
        f"  Entities in auth graph: {g.get('entities_in_auth_graph_pct')}%",
        f"  Published retrieval epoch: {r.get('published_index_epoch')}",
        f"  Retrieval org_link %: {r.get('org_link_pct')} | execution index %: {r.get('execution_index_pct')}",
        f"  Retrieval freshness (min): {r.get('freshness_minutes')}",
        f"  Synthesis artifacts with claims: {s.get('artifacts_with_claims')}",
    ]
    promos = g.get("promotions_by_rule_id") or []
    if promos:
        lines.append("  Promotions by rule_id:")
        for p in promos[:8]:
            lines.append(
                f"    - {p.get('rule_id')}: {p.get('unique_pairs')} unique pairs, "
                f"{p.get('auth_edge_rows')} rows"
            )
    return "\n".join(lines)
