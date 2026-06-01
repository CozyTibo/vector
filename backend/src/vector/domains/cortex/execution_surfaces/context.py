"""Tenant substrate coverage context for transparent omissions."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.resource_type_registry import disposition_by_resource_type
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.declared_domain import DeclaredDomain
from vector.infrastructure.db.models.graph_dirty_queue import GraphDirtyQueue
from vector.infrastructure.db.models.graph_relationship import STATUS_ACTIVE, GraphRelationship
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def _raw_count_for_prefix(session: Session, tenant_id: uuid.UUID, prefix: str) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.resource_type.like(f"{prefix}.%"),
            ),
        )
        or 0,
    )


def _canon_count_for_prefix(session: Session, tenant_id: uuid.UUID, prefix: str) -> int:
    return int(
        session.scalar(
            select(func.count(func.distinct(CanonEntitySource.canon_entity_id)))
            .join(CanonEntity, CanonEntity.id == CanonEntitySource.canon_entity_id)
            .where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntitySource.resource_type.like(f"{prefix}.%"),
            ),
        )
        or 0,
    )


def build_substrate_context(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    graph_dirty = int(
        session.scalar(
            select(func.count())
            .select_from(GraphDirtyQueue)
            .where(
                GraphDirtyQueue.tenant_id == tenant_id,
                GraphDirtyQueue.processed_at.is_(None),
            ),
        )
        or 0,
    )
    active_graph_edges = int(
        session.scalar(
            select(func.count())
            .select_from(GraphRelationship)
            .where(
                GraphRelationship.tenant_id == tenant_id,
                GraphRelationship.status == STATUS_ACTIVE,
            ),
        )
        or 0,
    )
    domain_count = int(
        session.scalar(
            select(func.count()).select_from(DeclaredDomain).where(DeclaredDomain.tenant_id == tenant_id),
        )
        or 0,
    )

    disposition = disposition_by_resource_type()
    calls_meeting_raw = _raw_count_for_prefix(session, tenant_id, "calls")
    calls_meeting_canon = _canon_count_for_prefix(session, tenant_id, "calls")
    calls_deferred = disposition.get("calls.meeting") == "defer"

    advisories: list[dict[str, str]] = []
    if graph_dirty > 0:
        advisories.append(
            {
                "code": "graph_backlog",
                "message": f"Graph projection backlog ({graph_dirty} dirty entities). Cross-tool expansion may be incomplete.",
                "remediation": "Run Graph pass from Links tab or wait for scheduler.",
            },
        )
    elif active_graph_edges == 0:
        advisories.append(
            {
                "code": "no_graph_edges",
                "message": "No active graph relationships in substrate.",
                "remediation": "Improve graph extraction — check Canon entities and run Graph pass.",
            },
        )
    if domain_count == 0:
        advisories.append(
            {
                "code": "no_declared_domains",
                "message": "No declared domains materialized.",
                "remediation": "Pin Notion work databases or connect Linear initiatives/projects, then run Declared Domains pass.",
            },
        )
    if calls_meeting_raw > 0 and (calls_deferred or calls_meeting_canon == 0):
        advisories.append(
            {
                "code": "calls_not_canonized",
                "message": f"Calls meetings ingested ({calls_meeting_raw} raw rows) but not canonized.",
                "remediation": "Canonize calls.meeting — currently deferred in resource registry.",
            },
        )

    return {
        "graph_dirty_pending": graph_dirty,
        "graph_expansion_incomplete": graph_dirty > 0,
        "active_graph_relationship_count": active_graph_edges,
        "declared_domain_count": domain_count,
        "calls_meeting_raw_count": calls_meeting_raw,
        "calls_meeting_canon_count": calls_meeting_canon,
        "calls_canon_deferred": calls_deferred,
        "advisories": advisories,
    }
