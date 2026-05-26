"""Authoritative link topology metrics (unique pairs, dup factor) — Wave S1 graph truth."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import nullslast, select, text
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.anchor_continuity_candidates import (
    RULE_GITHUB_LOGIN,
    RULE_SLACK_USER_ID,
)
from vector.domains.cortex.identity.identity_continuity_promotion_v1 import (
    count_promotable_link_candidates_by_rule_v1,
)
from vector.infrastructure.db.models.cortex_org_link_candidate_batch import CortexOrgLinkCandidateBatch

GRAPH_TRUTH_METRICS_SCHEMA_VERSION = 1
PROMOTION_DIVERSITY_ZERO_ALERT_AFTER = timedelta(hours=48)


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value)
    return int(value)


def snapshot_graph_substrate_isolation_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Isolation + largest auth component — primary phase 04 / substrate_truth KPIs (Wave 4)."""
    from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
        list_graph_connected_components_v1,
    )

    tid = str(tenant_id)
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
    isolated_pct = round(100.0 * isolated / active_entities, 2) if active_entities else 0.0
    in_graph_pct = round(100.0 * in_graph / active_entities, 2) if active_entities else 0.0

    components = list_graph_connected_components_v1(session, tenant_id=tenant_id)
    largest = max((len(c) for c in components), default=0)
    largest_component_entity_pct = (
        round(100.0 * largest / active_entities, 2) if active_entities else 0.0
    )

    return {
        "schema_version": GRAPH_TRUTH_METRICS_SCHEMA_VERSION,
        "tenant_id": tid,
        "active_entities": active_entities,
        "entities_in_auth_graph": in_graph,
        "entities_isolated": isolated,
        "entities_in_auth_graph_pct": in_graph_pct,
        "isolated_pct": isolated_pct,
        "entities_in_largest_auth_component": largest,
        "largest_component_entity_pct": largest_component_entity_pct,
        "auth_component_count": len(components),
        "primary_metric_keys": ("isolated_pct", "largest_component_entity_pct"),
    }


def snapshot_authoritative_link_topology_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Count active authoritative links using unique endpoint pairs (not projection edge lists)."""
    tid = str(tenant_id)
    row = session.execute(
        text(
            """
            SELECT
              COUNT(*)::bigint AS auth_edge_rows,
              COUNT(DISTINCT (source_entity_id, target_entity_id, link_type))::bigint
                AS unique_auth_pairs
            FROM cortex_org_links
            WHERE tenant_id = :tenant
              AND link_authority = 'authoritative'
              AND revoked_at IS NULL
            """
        ),
        {"tenant": tid},
    ).mappings().first()
    auth_edge_rows = _to_int(row["auth_edge_rows"]) if row else 0
    unique_auth_pairs = _to_int(row["unique_auth_pairs"]) if row else 0
    dup_factor: float | None = None
    if unique_auth_pairs > 0:
        dup_factor = round(auth_edge_rows / unique_auth_pairs, 3)
    return {
        "schema_version": GRAPH_TRUTH_METRICS_SCHEMA_VERSION,
        "tenant_id": tid,
        "auth_edge_rows": auth_edge_rows,
        "unique_auth_pairs": unique_auth_pairs,
        "dup_factor": dup_factor,
        "primary_metric_key": "unique_auth_pairs",
    }


def snapshot_promotion_diversity_observability_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Primary KPI: promotable candidates by rule; alert when Slack/GitHub stay at zero (S1.7)."""
    captured = now or datetime.now(UTC)
    promotable = count_promotable_link_candidates_by_rule_v1(session, tenant_id=tenant_id)
    by_rule = {row["rule_id"]: int(row["promotable_count"]) for row in promotable}
    slack_count = by_rule.get(RULE_SLACK_USER_ID, 0)
    github_count = by_rule.get(RULE_GITHUB_LOGIN, 0)
    slack_github_zero = slack_count == 0 and github_count == 0

    latest_batch = session.scalar(
        select(CortexOrgLinkCandidateBatch)
        .where(CortexOrgLinkCandidateBatch.tenant_id == tenant_id)
        .order_by(nullslast(CortexOrgLinkCandidateBatch.created_at.desc()), CortexOrgLinkCandidateBatch.id.asc())
        .limit(1)
    )
    batch_age_hours: float | None = None
    slack_github_zero_alert_48h = False
    if latest_batch is not None and latest_batch.created_at is not None:
        batch_age_hours = round((captured - latest_batch.created_at).total_seconds() / 3600.0, 2)
        if slack_github_zero and batch_age_hours >= PROMOTION_DIVERSITY_ZERO_ALERT_AFTER.total_seconds() / 3600.0:
            slack_github_zero_alert_48h = True

    severity = "ok"
    if slack_github_zero_alert_48h:
        severity = "bad"
    elif slack_github_zero:
        severity = "warn"

    return {
        "schema_version": GRAPH_TRUTH_METRICS_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "primary_kpi": "promotable_by_rule_id",
        "promotable_by_rule_id": promotable,
        "slack_promotable_count": slack_count,
        "github_promotable_count": github_count,
        "slack_github_promotable_zero": slack_github_zero,
        "slack_github_zero_alert_48h": slack_github_zero_alert_48h,
        "latest_candidate_batch_age_hours": batch_age_hours,
        "promotion_diversity_severity": severity,
    }


def snapshot_tcre_artifact_volume_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Completed TCRE job artifact counts — execution continuity substrate signal (S2.6)."""
    tid = str(tenant_id)
    rows = [
        dict(r)
        for r in session.execute(
            text(
                """
                SELECT a.artifact_kind, COUNT(*)::bigint AS n
                FROM cortex_tcre_reconstruction_artifacts a
                JOIN cortex_tcre_reconstruction_jobs j ON j.id = a.job_id
                WHERE j.tenant_id = :tenant AND j.status = 'completed'
                GROUP BY 1 ORDER BY n DESC, a.artifact_kind ASC
                """
            ),
            {"tenant": tid},
        ).mappings()
    ]
    total = sum(_to_int(r["n"]) for r in rows)
    return {
        "schema_version": GRAPH_TRUTH_METRICS_SCHEMA_VERSION,
        "tenant_id": tid,
        "tcre_artifact_count": total,
        "tcre_artifacts_by_kind": [
            {"artifact_kind": str(r["artifact_kind"]), "count": _to_int(r["n"])} for r in rows
        ],
    }


def snapshot_execution_continuity_admin_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Admin KPI bundle for artifact-backed execution continuity (not org-link topology)."""
    from vector.domains.cortex.continuity.edge_contracts import (
        list_continuity_edge_kinds_schema_only_v1,
    )

    tcre = snapshot_tcre_artifact_volume_v1(session, tenant_id=tenant_id)
    schema_only = list_continuity_edge_kinds_schema_only_v1()
    return {
        "tcre_artifact_count": tcre["tcre_artifact_count"],
        "tcre_artifacts_by_kind": tcre["tcre_artifacts_by_kind"],
        "continuity_edge_kinds_schema_only_non_kpi": schema_only,
        "continuity_edge_kind_count": len(schema_only),
    }
