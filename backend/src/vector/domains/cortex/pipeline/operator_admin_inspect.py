"""Operator inspect builders (R3 — graph snapshot, edge provenance, islands list)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.link_explorer import (
    list_org_link_explorer_rows,
    org_link_list_row_v1_from_link,
)
from vector.domains.cortex.operational_runtime.execution_island_registry import (
    list_execution_island_registry_v1,
)
from vector.domains.cortex.pipeline.admin_continuity_snapshot import read_admin_continuity_snapshot_v1
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink

_GRAPH_SNAPSHOT_STALE_MINUTES = 15


def build_operator_graph_snapshot_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Read materialized graph summary from continuity snapshot (no live component scan)."""
    snapshot = read_admin_continuity_snapshot_v1(session, tenant_id=tenant_id)
    captured_at = snapshot.get("captured_at_utc")
    stale = False
    if isinstance(captured_at, datetime):
        stale = datetime.now(UTC) - captured_at.replace(tzinfo=UTC) > timedelta(
            minutes=_GRAPH_SNAPSHOT_STALE_MINUTES
        )
    graph_summary = snapshot.get("graph_summary") if snapshot.get("available") else None
    identity_summary = snapshot.get("identity_summary") if snapshot.get("available") else None
    prose = _graph_snapshot_prose_v1(graph_summary if isinstance(graph_summary, dict) else None)
    return {
        "surface_kind": "operator_graph_snapshot_v1",
        "tenant_id": str(tenant_id),
        "available": bool(snapshot.get("available")),
        "captured_at_utc": captured_at,
        "stale": stale,
        "stale_after_minutes": _GRAPH_SNAPSHOT_STALE_MINUTES,
        "graph_summary": graph_summary,
        "identity_summary": identity_summary,
        "prose_summary": prose,
    }


def _graph_snapshot_prose_v1(graph: dict[str, Any] | None) -> str:
    if not graph:
        return "Graph continuity snapshot not yet materialized for this tenant."
    total = int(graph.get("entities_total") or 0)
    in_graph = int(graph.get("entities_in_graph") or 0)
    isolated = int(graph.get("isolated_entity_count") or 0)
    pairs = int(graph.get("unique_auth_pairs") or 0)
    pct = round(100.0 * in_graph / total, 1) if total > 0 else 0.0
    bits = [
        f"Auth graph connects {in_graph} of {total} entities ({pct}%).",
        f"{isolated} isolated entities.",
        f"{pairs} unique auth pairs.",
    ]
    slack = graph.get("promotable_slack")
    github = graph.get("promotable_github")
    if slack is not None or github is not None:
        bits.append(f"Promotable Slack/GitHub: {slack or 0}/{github or 0}.")
    return " ".join(bits)


def _edge_provenance_detail_v1(row: CortexOrgLink) -> dict[str, Any]:
    meta = dict(row.metadata_json or {})
    base = org_link_list_row_v1_from_link(row)
    return {
        **base,
        "source_entity_id": str(row.source_entity_id),
        "target_entity_id": str(row.target_entity_id),
        "rule_id": row.rule_id,
        "link_authority": row.link_authority,
        "link_class": row.link_class,
        "promoted_from_candidate_id": (
            str(row.promoted_from_candidate_id) if row.promoted_from_candidate_id else None
        ),
        "promotion_batch_id": meta.get("promotion_batch_id"),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
        "evidence_raw_record_ids": list(row.evidence_raw_record_ids or []),
        "metadata_json": meta,
    }


def lookup_edge_provenance_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_entity_id: uuid.UUID | None = None,
    target_entity_id: uuid.UUID | None = None,
    link_id: uuid.UUID | None = None,
    link_type: str | None = None,
    rule_id: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """On-demand edge lookup — link row, rule, promotion batch, evidence ids."""
    lim = max(1, min(int(limit), 200))

    if link_id is not None:
        row = session.get(CortexOrgLink, link_id)
        edges = (
            [_edge_provenance_detail_v1(row)]
            if row is not None and row.tenant_id == tenant_id
            else []
        )
        return {
            "surface_kind": "operator_edge_provenance_v1",
            "tenant_id": str(tenant_id),
            "query": {"link_id": str(link_id)},
            "edges": edges,
            "total": len(edges),
        }

    if source_entity_id is None and target_entity_id is None and not link_type and not rule_id:
        raise ValueError("edge_query_required")

    stmt = select(CortexOrgLink).where(CortexOrgLink.tenant_id == tenant_id)
    if source_entity_id is not None:
        stmt = stmt.where(
            or_(
                CortexOrgLink.source_entity_id == source_entity_id,
                CortexOrgLink.target_entity_id == source_entity_id,
            )
        )
    if target_entity_id is not None:
        stmt = stmt.where(
            or_(
                CortexOrgLink.source_entity_id == target_entity_id,
                CortexOrgLink.target_entity_id == target_entity_id,
            )
        )
    if link_type and link_type.strip():
        stmt = stmt.where(CortexOrgLink.link_type == link_type.strip())
    if rule_id and rule_id.strip():
        rv = rule_id.strip()
        stmt = stmt.where(
            or_(
                CortexOrgLink.rule_id == rv,
                CortexOrgLink.metadata_json["link_rule_version_id"].astext == rv,
            )
        )

    rows = list(
        session.scalars(
            stmt.order_by(CortexOrgLink.created_at.desc()).limit(lim)
        ).all()
    )

    if not rows and source_entity_id is not None:
        explorer_rows = list_org_link_explorer_rows(
            session,
            tenant_id=tenant_id,
            handle_id=source_entity_id,
            limit=lim,
        )
        return {
            "surface_kind": "operator_edge_provenance_v1",
            "tenant_id": str(tenant_id),
            "query": {
                "source_entity_id": str(source_entity_id),
                "target_entity_id": str(target_entity_id) if target_entity_id else None,
                "link_type": link_type,
                "rule_id": rule_id,
            },
            "edges": explorer_rows,
            "total": len(explorer_rows),
        }

    edges = [_edge_provenance_detail_v1(row) for row in rows]
    return {
        "surface_kind": "operator_edge_provenance_v1",
        "tenant_id": str(tenant_id),
        "query": {
            "source_entity_id": str(source_entity_id) if source_entity_id else None,
            "target_entity_id": str(target_entity_id) if target_entity_id else None,
            "link_type": link_type,
            "rule_id": rule_id,
        },
        "edges": edges,
        "total": len(edges),
    }


def build_operator_islands_list_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Registry-first island list — no connected-component scan."""
    islands = list_execution_island_registry_v1(session, tenant_id=tenant_id)
    return {
        "surface_kind": "operator_islands_list_v1",
        "tenant_id": str(tenant_id),
        "island_count": len(islands),
        "islands": islands,
    }
