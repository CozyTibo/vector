"""Declared domain membership expansion (Level 0 + Level 1)."""

from __future__ import annotations

import uuid
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.declared_container_registry import (
    ATTR_DECLARED_CONTAINER_EXTERNAL_ID,
    work_item_matches_container,
)
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain import DeclaredDomain
from vector.infrastructure.db.models.declared_domain_membership import (
    DeclaredDomainMembership,
    STATUS_ACTIVE,
    STATUS_SUPERSEDED,
)
from vector.infrastructure.db.models.graph_relationship import GraphRelationship, STATUS_ACTIVE as GRAPH_ACTIVE

EXPANSION_DIRECT = "direct"
EXPANSION_GRAPH = "graph"

RULE_DIRECT_CONTAINER_REF = "direct.container_ref"
RULE_DIRECT_SEED = "direct.seed_entity"

GRAPH_RULE_BY_KIND: dict[str, str] = {
    "closes": "graph.closes",
    "references": "graph.references",
    "mentions": "graph.mentions",
    "comments_on": "graph.comments_on",
    "replies_to": "graph.replies_to",
    "parent_of": "graph.parent_of",
}

ALLOWED_GRAPH_KINDS = frozenset(GRAPH_RULE_BY_KIND)
ALLOWED_MEMBERSHIP_ENTITY_TYPES = frozenset(
    {
        "work_item",
        "pull_request",
        "message",
        "conversation",
        "document",
        "commit",
        "deployment",
    },
)
ALLOWED_GRAPH_CONFIDENCE = frozenset({"certain", "high"})


@dataclass(frozen=True, slots=True)
class MembershipDraft:
    canon_entity_id: uuid.UUID
    extractor_rule: str
    expansion_level: str
    evidence_kind: str
    evidence_ref: str
    seed_distance: int
    observed_at: datetime


def _seed_external_id(seed_entity: CanonEntity) -> str | None:
    attrs = seed_entity.attrs_json if isinstance(seed_entity.attrs_json, dict) else {}
    ext = attrs.get(ATTR_DECLARED_CONTAINER_EXTERNAL_ID)
    return ext if isinstance(ext, str) and ext else None


def supersede_active_memberships(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    declared_domain_id: uuid.UUID,
) -> int:
    now = utc_now()
    result = session.execute(
        update(DeclaredDomainMembership)
        .where(
            DeclaredDomainMembership.tenant_id == tenant_id,
            DeclaredDomainMembership.declared_domain_id == declared_domain_id,
            DeclaredDomainMembership.status == STATUS_ACTIVE,
        )
        .values(status=STATUS_SUPERSEDED, superseded_at=now),
    )
    return int(result.rowcount or 0)


def _collect_level0_memberships(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    domain: DeclaredDomain,
    seed_entity: CanonEntity,
    extractor_version: int,
    observed_at: datetime,
) -> list[MembershipDraft]:
    drafts: list[MembershipDraft] = []
    container_external_id = _seed_external_id(seed_entity)
    if container_external_id is None:
        return drafts

    if seed_entity.entity_type in ALLOWED_MEMBERSHIP_ENTITY_TYPES:
        drafts.append(
            MembershipDraft(
                canon_entity_id=seed_entity.id,
                extractor_rule=RULE_DIRECT_SEED,
                expansion_level=EXPANSION_DIRECT,
                evidence_kind="seed",
                evidence_ref=str(seed_entity.id),
                seed_distance=0,
                observed_at=observed_at,
            ),
        )

    work_items = session.scalars(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.entity_type == "work_item",
        ),
    ).all()
    for work_item in work_items:
        attrs = work_item.attrs_json if isinstance(work_item.attrs_json, dict) else {}
        if work_item_matches_container(
            attrs,
            container_kind=domain.declared_container_kind,
            container_external_id=container_external_id,
        ):
            drafts.append(
                MembershipDraft(
                    canon_entity_id=work_item.id,
                    extractor_rule=RULE_DIRECT_CONTAINER_REF,
                    expansion_level=EXPANSION_DIRECT,
                    evidence_kind="container_ref",
                    evidence_ref=f"{domain.declared_container_kind}:{container_external_id}",
                    seed_distance=0,
                    observed_at=observed_at,
                ),
            )
    return drafts


def _graph_neighbors(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> list[tuple[uuid.UUID, str, str]]:
    """Return (neighbor_id, relationship_kind, edge_id) for high-confidence active edges."""
    out: list[tuple[uuid.UUID, str, str]] = []
    edges = session.scalars(
        select(GraphRelationship).where(
            GraphRelationship.tenant_id == tenant_id,
            GraphRelationship.status == GRAPH_ACTIVE,
            GraphRelationship.confidence.in_(tuple(ALLOWED_GRAPH_CONFIDENCE)),
            GraphRelationship.relationship_kind.in_(tuple(ALLOWED_GRAPH_KINDS)),
            (
                (GraphRelationship.from_entity_id == entity_id)
                | (GraphRelationship.to_entity_id == entity_id)
            ),
        ),
    ).all()
    for edge in edges:
        neighbor = edge.to_entity_id if edge.from_entity_id == entity_id else edge.from_entity_id
        out.append((neighbor, edge.relationship_kind, str(edge.id)))
    return out


def _collect_level1_memberships(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    direct_drafts: Iterable[MembershipDraft],
    max_depth: int,
    observed_at: datetime,
) -> list[MembershipDraft]:
    if max_depth <= 0:
        return []
    direct_ids = {d.canon_entity_id for d in direct_drafts}
    seen: set[uuid.UUID] = set(direct_ids)
    drafts: list[MembershipDraft] = []
    queue: deque[tuple[uuid.UUID, int]] = deque((entity_id, 0) for entity_id in direct_ids)

    while queue:
        current_id, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for neighbor_id, kind, edge_id in _graph_neighbors(
            session,
            tenant_id=tenant_id,
            entity_id=current_id,
        ):
            if neighbor_id in seen:
                continue
            entity = session.get(CanonEntity, neighbor_id)
            if entity is None or entity.tenant_id != tenant_id:
                continue
            if entity.entity_type not in ALLOWED_MEMBERSHIP_ENTITY_TYPES:
                continue
            seen.add(neighbor_id)
            rule = GRAPH_RULE_BY_KIND.get(kind, f"graph.{kind}")
            drafts.append(
                MembershipDraft(
                    canon_entity_id=neighbor_id,
                    extractor_rule=rule,
                    expansion_level=EXPANSION_GRAPH,
                    evidence_kind="graph_edge",
                    evidence_ref=edge_id,
                    seed_distance=depth + 1,
                    observed_at=observed_at,
                ),
            )
            queue.append((neighbor_id, depth + 1))
    return drafts


def persist_membership_drafts(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    declared_domain_id: uuid.UUID,
    drafts: Iterable[MembershipDraft],
    extractor_version: int,
) -> int:
    now = utc_now()
    inserted = 0
    for draft in drafts:
        session.add(
            DeclaredDomainMembership(
                tenant_id=tenant_id,
                declared_domain_id=declared_domain_id,
                canon_entity_id=draft.canon_entity_id,
                extractor_version=extractor_version,
                extractor_rule=draft.extractor_rule,
                expansion_level=draft.expansion_level,
                evidence_kind=draft.evidence_kind,
                evidence_ref=draft.evidence_ref,
                seed_distance=draft.seed_distance,
                observed_at=draft.observed_at,
                status=STATUS_ACTIVE,
                created_at=now,
            ),
        )
        inserted += 1
    return inserted


def refresh_domain_memberships(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    domain: DeclaredDomain,
    seed_entity: CanonEntity,
    extractor_version: int,
    expansion_max_depth: int,
    graph_expansion_enabled: bool,
) -> dict[str, int | str]:
    """Rebuild memberships for one domain (Level 0 always; Level 1 when enabled)."""
    observed_at = utc_now()
    supersede_active_memberships(
        session,
        tenant_id=tenant_id,
        declared_domain_id=domain.id,
    )
    level0 = _collect_level0_memberships(
        session,
        tenant_id=tenant_id,
        domain=domain,
        seed_entity=seed_entity,
        extractor_version=extractor_version,
        observed_at=observed_at,
    )
    level1: list[MembershipDraft] = []
    if graph_expansion_enabled:
        level1 = _collect_level1_memberships(
            session,
            tenant_id=tenant_id,
            direct_drafts=level0,
            max_depth=expansion_max_depth,
            observed_at=observed_at,
        )

    # Prefer direct membership when same entity reached via graph.
    by_entity: dict[uuid.UUID, MembershipDraft] = {}
    for draft in level0:
        by_entity[draft.canon_entity_id] = draft
    for draft in level1:
        by_entity.setdefault(draft.canon_entity_id, draft)

    inserted = persist_membership_drafts(
        session,
        tenant_id=tenant_id,
        declared_domain_id=domain.id,
        drafts=by_entity.values(),
        extractor_version=extractor_version,
    )
    expansion_level = "direct"
    if graph_expansion_enabled and level1:
        expansion_level = "graph_current"
    elif graph_expansion_enabled:
        expansion_level = "partial_graph"
    return {
        "memberships_inserted": inserted,
        "level0_count": len(level0),
        "level1_count": len(level1),
        "expansion_level": expansion_level,
    }
