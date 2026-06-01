"""Observation activity stream — graph and membership signals only (not execution timeline)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.notion_display_labels import enrich_notion_display_labels
from vector.domains.cortex.execution_surfaces.omissions import EXECUTION_ACTIVITY_UNAVAILABLE_FOOTNOTE
from vector.domains.cortex.graph.relationship_kinds import label_for_kind
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain_membership import (
    DeclaredDomainMembership,
    STATUS_ACTIVE,
)
from vector.infrastructure.db.models.graph_relationship import STATUS_ACTIVE as GRAPH_ACTIVE
from vector.infrastructure.db.models.graph_relationship import GraphRelationship
from vector.infrastructure.db.models.identity_account import IdentityAccount


def _stable_event_id(kind: str, source_id: str, observed_at: str) -> str:
    raw = f"{kind}:{source_id}:{observed_at}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _entity_brief(entity: CanonEntity, labels: dict[uuid.UUID, str]) -> dict[str, Any]:
    return {
        "canon_entity_id": str(entity.id),
        "entity_type": entity.entity_type,
        "connector": entity.connector,
        "display_label": labels.get(entity.id, entity.display_label),
    }


def list_observation_activity(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    identity_id: uuid.UUID | None = None,
    domain_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    hours: int = 168,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int, dict[str, Any]]:
    """Return chronologically sorted observation signals (not operational execution events)."""
    now = utc_now()
    window_start = now - timedelta(hours=max(1, min(hours, 24 * 30)))

    member_entity_ids: set[uuid.UUID] | None = None
    if domain_id is not None:
        member_entity_ids = set(
            session.scalars(
                select(DeclaredDomainMembership.canon_entity_id).where(
                    DeclaredDomainMembership.tenant_id == tenant_id,
                    DeclaredDomainMembership.declared_domain_id == domain_id,
                    DeclaredDomainMembership.status == STATUS_ACTIVE,
                ),
            ).all(),
        )

    actor_entity_ids: set[uuid.UUID] | None = None
    if identity_id is not None:
        actor_entity_ids = set(
            session.scalars(
                select(IdentityAccount.canon_entity_id).where(
                    IdentityAccount.tenant_id == tenant_id,
                    IdentityAccount.identity_entity_id == identity_id,
                    IdentityAccount.unlinked_at.is_(None),
                ),
            ).all(),
        )

    graph_stmt = select(GraphRelationship).where(
        GraphRelationship.tenant_id == tenant_id,
        GraphRelationship.status == GRAPH_ACTIVE,
        GraphRelationship.observed_at >= window_start,
    )
    if member_entity_ids is not None:
        graph_stmt = graph_stmt.where(
            or_(
                GraphRelationship.from_entity_id.in_(member_entity_ids),
                GraphRelationship.to_entity_id.in_(member_entity_ids),
            ),
        )

    graph_rows = list(session.scalars(graph_stmt.order_by(GraphRelationship.observed_at.desc())).all())

    membership_stmt = select(DeclaredDomainMembership).where(
        DeclaredDomainMembership.tenant_id == tenant_id,
        DeclaredDomainMembership.status == STATUS_ACTIVE,
        DeclaredDomainMembership.observed_at >= window_start,
    )
    if domain_id is not None:
        membership_stmt = membership_stmt.where(
            DeclaredDomainMembership.declared_domain_id == domain_id,
        )
    membership_rows = list(
        session.scalars(membership_stmt.order_by(DeclaredDomainMembership.observed_at.desc())).all(),
    )

    entity_ids: set[uuid.UUID] = set()
    for row in graph_rows:
        entity_ids.add(row.from_entity_id)
        entity_ids.add(row.to_entity_id)
    for row in membership_rows:
        entity_ids.add(row.canon_entity_id)

    entities: dict[uuid.UUID, CanonEntity] = {}
    if entity_ids:
        for ent in session.scalars(
            select(CanonEntity).where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.id.in_(entity_ids),
            ),
        ).all():
            entities[ent.id] = ent

    labels = enrich_notion_display_labels(session, entities.values())
    events: list[dict[str, Any]] = []

    for row in graph_rows:
        from_ent = entities.get(row.from_entity_id)
        to_ent = entities.get(row.to_entity_id)
        if from_ent is None or to_ent is None:
            continue
        if entity_type and from_ent.entity_type != entity_type and to_ent.entity_type != entity_type:
            continue
        if identity_id is not None:
            identity_match = row.from_identity_id == identity_id or row.to_identity_id == identity_id
            actor_match = False
            if actor_entity_ids:
                actor_match = (
                    from_ent.author_entity_id in actor_entity_ids
                    or from_ent.assignee_entity_id in actor_entity_ids
                    or to_ent.author_entity_id in actor_entity_ids
                    or to_ent.assignee_entity_id in actor_entity_ids
                    or from_ent.id in actor_entity_ids
                    or to_ent.id in actor_entity_ids
                )
            if not identity_match and not actor_match:
                continue
        observed = row.observed_at.isoformat()
        events.append(
            {
                "id": _stable_event_id("relationship_observed", str(row.id), observed),
                "event_kind": "relationship_observed",
                "observed_at": observed,
                "label": f"Relationship recorded: {label_for_kind(row.relationship_kind)}",
                "primary_entity": _entity_brief(from_ent, labels),
                "related_entity": _entity_brief(to_ent, labels),
                "domain_ids": [str(domain_id)] if domain_id else [],
                "identity_ids": [str(identity_id)] if identity_id else [],
                "provenance": {
                    "kind": "graph_relationship",
                    "id": str(row.id),
                    "relationship_kind": row.relationship_kind,
                    "extractor_rule": row.extractor_rule,
                    "evidence_kind": row.evidence_kind,
                    "evidence_ref": row.evidence_ref,
                    "confidence": row.confidence,
                },
            },
        )

    for row in membership_rows:
        ent = entities.get(row.canon_entity_id)
        if ent is None:
            continue
        if entity_type and ent.entity_type != entity_type:
            continue
        observed = row.observed_at.isoformat()
        events.append(
            {
                "id": _stable_event_id("membership_observed", str(row.id), observed),
                "event_kind": "membership_observed",
                "observed_at": observed,
                "label": "Domain membership recorded by Cortex",
                "primary_entity": _entity_brief(ent, labels),
                "related_entity": None,
                "domain_ids": [str(row.declared_domain_id)],
                "identity_ids": [],
                "provenance": {
                    "kind": "declared_domain_membership",
                    "id": str(row.id),
                    "extractor_rule": row.extractor_rule,
                    "evidence_kind": row.evidence_kind,
                    "evidence_ref": row.evidence_ref,
                },
            },
        )

    events.sort(key=lambda e: e["observed_at"], reverse=True)
    total = len(events)
    page = events[offset : offset + limit]

    meta = {
        "execution_timeline_available": False,
        "footnote": EXECUTION_ACTIVITY_UNAVAILABLE_FOOTNOTE,
        "window_hours": hours,
    }
    return page, total, meta
