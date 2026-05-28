"""Admin-facing graph read APIs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.graph.extractor_version import (
    GRAPH_EXTRACTOR_VERSION,
    effective_graph_extractor_version,
)
from vector.domains.cortex.graph.pass_run_ops import abandon_stuck_running_graph_passes
from vector.domains.cortex.graph.relationship_kinds import label_for_kind
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.graph_dirty_queue import GraphDirtyQueue
from vector.infrastructure.db.models.graph_pass_run import GraphPassRun
from vector.infrastructure.db.models.graph_relationship import STATUS_ACTIVE, GraphRelationship
from vector.infrastructure.db.models.graph_unresolved_reference import GraphUnresolvedReference
from vector.infrastructure.db.models.identity_entity import IdentityEntity

MANUAL_GRAPH_PASS_CONFIRMATION = "RUN GRAPH PROJECTION PASS"
MANUAL_GRAPH_REBUILD_CONFIRMATION = "REBUILD GRAPH PROJECTIONS"


def build_graph_readiness(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    scheduler: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dirty_pending = int(
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
    active_edges = int(
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
    latest = session.scalar(
        select(GraphPassRun)
        .where(GraphPassRun.tenant_id == tenant_id)
        .order_by(GraphPassRun.started_at.desc())
        .limit(1),
    )
    latest_payload: dict[str, Any] | None = None
    if latest is not None:
        latest_payload = {
            "id": str(latest.id),
            "status": latest.status,
            "source_trigger": latest.source_trigger,
            "started_at": latest.started_at.isoformat(),
            "finished_at": latest.finished_at.isoformat() if latest.finished_at else None,
            "stats": latest.stats or {},
            "error_summary": latest.error_summary,
        }
    return {
        "tenant_id": str(tenant_id),
        "extractor_version": effective_graph_extractor_version(None),
        "extractor_version_code": GRAPH_EXTRACTOR_VERSION,
        "dirty_queue_pending": dirty_pending,
        "active_relationship_count": active_edges,
        "latest_pass_run": latest_payload,
        "scheduler": scheduler or {},
    }


def _entity_summary(entity: CanonEntity) -> dict[str, Any]:
    return {
        "entity_id": str(entity.id),
        "entity_type": entity.entity_type,
        "connector": entity.connector,
        "display_label": entity.display_label,
        "entity_key": entity.entity_key,
    }


def _identity_summary(session: Session, identity_id: uuid.UUID | None) -> dict[str, Any] | None:
    if identity_id is None:
        return None
    row = session.get(IdentityEntity, identity_id)
    if row is None:
        return None
    return {
        "identity_id": str(row.id),
        "display_name": row.display_name,
        "kind": row.kind,
    }


def list_relationships(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    relationship_kind: str | None = None,
    entity_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    stmt = select(GraphRelationship).where(
        GraphRelationship.tenant_id == tenant_id,
        GraphRelationship.status == STATUS_ACTIVE,
    )
    if relationship_kind:
        stmt = stmt.where(GraphRelationship.relationship_kind == relationship_kind)
    if entity_id is not None:
        stmt = stmt.where(
            (GraphRelationship.from_entity_id == entity_id)
            | (GraphRelationship.to_entity_id == entity_id),
        )
    count_stmt = select(func.count()).select_from(GraphRelationship).where(
        GraphRelationship.tenant_id == tenant_id,
        GraphRelationship.status == STATUS_ACTIVE,
    )
    if relationship_kind:
        count_stmt = count_stmt.where(GraphRelationship.relationship_kind == relationship_kind)
    if entity_id is not None:
        count_stmt = count_stmt.where(
            (GraphRelationship.from_entity_id == entity_id)
            | (GraphRelationship.to_entity_id == entity_id),
        )
    total = int(session.scalar(count_stmt) or 0)
    rows = list(
        session.scalars(
            stmt.order_by(GraphRelationship.observed_at.desc()).offset(offset).limit(limit),
        ).all(),
    )
    entity_ids: set[uuid.UUID] = set()
    for row in rows:
        entity_ids.add(row.from_entity_id)
        entity_ids.add(row.to_entity_id)
    entities: dict[uuid.UUID, CanonEntity] = {}
    if entity_ids:
        for ent in session.scalars(select(CanonEntity).where(CanonEntity.id.in_(entity_ids))).all():
            entities[ent.id] = ent

    items: list[dict[str, Any]] = []
    for row in rows:
        from_ent = entities.get(row.from_entity_id)
        to_ent = entities.get(row.to_entity_id)
        items.append(
            {
                "id": str(row.id),
                "relationship_kind": row.relationship_kind,
                "relationship_kind_label": label_for_kind(row.relationship_kind),
                "confidence": row.confidence,
                "extractor_rule": row.extractor_rule,
                "observed_at": row.observed_at.isoformat(),
                "from": (
                    _entity_summary(from_ent)
                    if from_ent
                    else {"entity_id": str(row.from_entity_id)}
                ),
                "to": (
                    _entity_summary(to_ent) if to_ent else {"entity_id": str(row.to_entity_id)}
                ),
                "from_identity": _identity_summary(session, row.from_identity_id),
                "to_identity": _identity_summary(session, row.to_identity_id),
                "evidence_snapshot": row.evidence_snapshot or {},
                "source_raw_id": row.source_raw_id,
            },
        )
    return items, total


def get_relationship_detail(
    session: Session,
    tenant_id: uuid.UUID,
    relationship_id: uuid.UUID,
) -> dict[str, Any] | None:
    row = session.get(GraphRelationship, relationship_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    from_ent = session.get(CanonEntity, row.from_entity_id)
    to_ent = session.get(CanonEntity, row.to_entity_id)
    return {
        "id": str(row.id),
        "relationship_kind": row.relationship_kind,
        "relationship_kind_label": label_for_kind(row.relationship_kind),
        "confidence": row.confidence,
        "extractor_rule": row.extractor_rule,
        "extractor_version": row.extractor_version,
        "evidence_kind": row.evidence_kind,
        "evidence_ref": row.evidence_ref,
        "observed_at": row.observed_at.isoformat(),
        "status": row.status,
        "from": _entity_summary(from_ent) if from_ent else None,
        "to": _entity_summary(to_ent) if to_ent else None,
        "from_identity": _identity_summary(session, row.from_identity_id),
        "to_identity": _identity_summary(session, row.to_identity_id),
        "evidence_snapshot": row.evidence_snapshot or {},
        "source_raw_id": row.source_raw_id,
        "source_canon_source_id": (
            str(row.source_canon_source_id) if row.source_canon_source_id else None
        ),
    }


def list_entity_links(
    session: Session,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
    *,
    direction: str = "both",
    limit: int = 50,
) -> dict[str, Any]:
    outbound: list[dict[str, Any]] = []
    inbound: list[dict[str, Any]] = []
    if direction in ("both", "outbound"):
        items, _ = list_relationships(
            session,
            tenant_id,
            entity_id=entity_id,
            limit=limit,
            offset=0,
        )
        outbound = [i for i in items if i["from"]["entity_id"] == str(entity_id)]
    if direction in ("both", "inbound"):
        stmt = (
            select(GraphRelationship)
            .where(
                GraphRelationship.tenant_id == tenant_id,
                GraphRelationship.status == STATUS_ACTIVE,
                GraphRelationship.to_entity_id == entity_id,
            )
            .order_by(GraphRelationship.observed_at.desc())
            .limit(limit)
        )
        rows = list(session.scalars(stmt).all())
        entity_ids = {r.from_entity_id for r in rows}
        entities = {
            e.id: e
            for e in session.scalars(
                select(CanonEntity).where(CanonEntity.id.in_(entity_ids)),
            ).all()
        }
        for row in rows:
            from_ent = entities.get(row.from_entity_id)
            inbound.append(
                {
                    "id": str(row.id),
                    "relationship_kind": row.relationship_kind,
                    "relationship_kind_label": label_for_kind(row.relationship_kind),
                    "confidence": row.confidence,
                    "extractor_rule": row.extractor_rule,
                    "observed_at": row.observed_at.isoformat(),
                    "from": (
                        _entity_summary(from_ent)
                        if from_ent
                        else {"entity_id": str(row.from_entity_id)}
                    ),
                    "to": {"entity_id": str(entity_id)},
                    "from_identity": _identity_summary(session, row.from_identity_id),
                    "to_identity": _identity_summary(session, row.to_identity_id),
                    "evidence_snapshot": row.evidence_snapshot or {},
                    "source_raw_id": row.source_raw_id,
                },
            )
    return {"outbound": outbound, "inbound": inbound}


def graph_stats_by_kind(session: Session, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = session.execute(
        select(GraphRelationship.relationship_kind, func.count())
        .where(
            GraphRelationship.tenant_id == tenant_id,
            GraphRelationship.status == STATUS_ACTIVE,
        )
        .group_by(GraphRelationship.relationship_kind)
        .order_by(func.count().desc()),
    ).all()
    return [
        {
            "relationship_kind": kind,
            "relationship_kind_label": label_for_kind(str(kind)),
            "count": int(count),
        }
        for kind, count in rows
    ]


def list_recent_graph_pass_runs(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    base = select(GraphPassRun).where(GraphPassRun.tenant_id == tenant_id)
    total = int(session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = list(
        session.scalars(
            base.order_by(GraphPassRun.started_at.desc()).offset(offset).limit(limit),
        ).all(),
    )
    items = [
        {
            "id": str(r.id),
            "source_trigger": r.source_trigger,
            "status": r.status,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "stats": r.stats or {},
            "error_summary": r.error_summary,
        }
        for r in rows
    ]
    return items, total


def list_unresolved_references(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    base = select(GraphUnresolvedReference).where(
        GraphUnresolvedReference.tenant_id == tenant_id,
        GraphUnresolvedReference.status == "unresolved",
    )
    total = int(session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = list(
        session.scalars(
            base.order_by(GraphUnresolvedReference.created_at.desc())
            .offset(offset)
            .limit(limit),
        ).all(),
    )
    items: list[dict[str, Any]] = []
    for row in rows:
        source = session.get(CanonEntity, row.source_entity_id)
        items.append(
            {
                "id": str(row.id),
                "reference_kind": row.reference_kind,
                "reference_text": row.reference_text,
                "extractor_rule": row.extractor_rule,
                "created_at": row.created_at.isoformat(),
                "source_entity": _entity_summary(source) if source else None,
                "evidence_snapshot": row.evidence_snapshot or {},
            },
        )
    return items, total


def prepare_graph_pass_trigger(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    interval_seconds: int,
) -> int:
    return abandon_stuck_running_graph_passes(
        session,
        tenant_id=tenant_id,
        interval_seconds=interval_seconds,
    )
