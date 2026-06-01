"""People (identity) composition for Execution Surfaces."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution_surfaces.omissions import OBSERVATION_ACTIVITY_FOOTNOTE
from vector.domains.cortex.identity.admin import get_identity_detail, list_identities
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain_membership import (
    DeclaredDomainMembership,
    STATUS_ACTIVE,
)
from vector.infrastructure.db.models.declared_domain import DeclaredDomain
from vector.infrastructure.db.models.graph_relationship import STATUS_ACTIVE as GRAPH_ACTIVE
from vector.infrastructure.db.models.graph_relationship import GraphRelationship
from vector.infrastructure.db.models.identity_account import IdentityAccount


def _touch_counts_for_identity(
    session: Session,
    tenant_id: uuid.UUID,
    identity_id: uuid.UUID,
) -> dict[str, int]:
    accounts = list(
        session.scalars(
            select(IdentityAccount).where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.identity_entity_id == identity_id,
                IdentityAccount.unlinked_at.is_(None),
            ),
        ).all(),
    )
    actor_ids = {a.canon_entity_id for a in accounts}
    if not actor_ids:
        return {"work_items": 0, "pull_requests": 0, "messages": 0, "graph_edges": 0, "domains": 0}

    work_items = int(
        session.scalar(
            select(func.count())
            .select_from(CanonEntity)
            .where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.entity_type == "work_item",
                or_(
                    CanonEntity.assignee_entity_id.in_(actor_ids),
                    CanonEntity.author_entity_id.in_(actor_ids),
                ),
            ),
        )
        or 0,
    )
    prs = int(
        session.scalar(
            select(func.count())
            .select_from(CanonEntity)
            .where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.entity_type == "pull_request",
                CanonEntity.author_entity_id.in_(actor_ids),
            ),
        )
        or 0,
    )
    messages = int(
        session.scalar(
            select(func.count())
            .select_from(CanonEntity)
            .where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.entity_type == "message",
                CanonEntity.author_entity_id.in_(actor_ids),
            ),
        )
        or 0,
    )
    graph_edges = int(
        session.scalar(
            select(func.count())
            .select_from(GraphRelationship)
            .where(
                GraphRelationship.tenant_id == tenant_id,
                GraphRelationship.status == GRAPH_ACTIVE,
                or_(
                    GraphRelationship.from_entity_id.in_(actor_ids),
                    GraphRelationship.to_entity_id.in_(actor_ids),
                ),
            ),
        )
        or 0,
    )

    member_entity_ids_subq = (
        select(DeclaredDomainMembership.canon_entity_id)
        .where(
            DeclaredDomainMembership.tenant_id == tenant_id,
            DeclaredDomainMembership.status == STATUS_ACTIVE,
            or_(
                DeclaredDomainMembership.canon_entity_id.in_(
                    select(CanonEntity.id).where(
                        CanonEntity.assignee_entity_id.in_(actor_ids),
                    ),
                ),
            ),
        )
        .distinct()
    )
    domains = int(
        session.scalar(
            select(func.count(func.distinct(DeclaredDomainMembership.declared_domain_id)))
            .where(
                DeclaredDomainMembership.tenant_id == tenant_id,
                DeclaredDomainMembership.status == STATUS_ACTIVE,
                DeclaredDomainMembership.canon_entity_id.in_(member_entity_ids_subq),
            ),
        )
        or 0,
    )

    return {
        "work_items": work_items,
        "pull_requests": prs,
        "messages": messages,
        "graph_edges": graph_edges,
        "domains": domains,
    }


def list_people_for_surface(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    items, total = list_identities(session, tenant_id, kind=None, limit=limit, offset=offset, search=search)
    for item in items:
        touch = _touch_counts_for_identity(session, tenant_id, uuid.UUID(item["id"]))
        item["participation"] = {**touch, "footnote": OBSERVATION_ACTIVITY_FOOTNOTE}
    return items, total


def get_person_surface_detail(
    session: Session,
    tenant_id: uuid.UUID,
    identity_id: uuid.UUID,
) -> dict[str, Any] | None:
    detail = get_identity_detail(session, tenant_id, identity_id)
    if detail is None:
        return None
    touch = _touch_counts_for_identity(session, tenant_id, identity_id)
    detail["participation"] = {**touch, "footnote": OBSERVATION_ACTIVITY_FOOTNOTE}
    detail["domains"] = _domains_for_identity(session, tenant_id, identity_id)
    return detail


def _domains_for_identity(
    session: Session,
    tenant_id: uuid.UUID,
    identity_id: uuid.UUID,
) -> list[dict[str, Any]]:
    accounts = list(
        session.scalars(
            select(IdentityAccount).where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.identity_entity_id == identity_id,
                IdentityAccount.unlinked_at.is_(None),
            ),
        ).all(),
    )
    actor_ids = {a.canon_entity_id for a in accounts}
    if not actor_ids:
        return []
    domain_ids = {
        row
        for row in session.scalars(
            select(DeclaredDomainMembership.declared_domain_id)
            .join(CanonEntity, CanonEntity.id == DeclaredDomainMembership.canon_entity_id)
            .where(
                DeclaredDomainMembership.tenant_id == tenant_id,
                DeclaredDomainMembership.status == STATUS_ACTIVE,
                or_(
                    CanonEntity.assignee_entity_id.in_(actor_ids),
                    CanonEntity.author_entity_id.in_(actor_ids),
                ),
            )
            .distinct(),
        ).all()
    }
    if not domain_ids:
        return []
    domains = list(
        session.scalars(select(DeclaredDomain).where(DeclaredDomain.id.in_(domain_ids))).all(),
    )
    return [
        {
            "id": str(d.id),
            "display_name": d.display_name,
            "declared_container_kind": d.declared_container_kind,
        }
        for d in domains
    ]
