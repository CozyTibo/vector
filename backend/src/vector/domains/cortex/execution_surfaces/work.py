"""Work artifact explorer for Execution Surfaces."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.notion_display_labels import enrich_notion_display_labels
from vector.domains.cortex.execution_surfaces.omissions import section, with_items
from vector.domains.cortex.graph.admin import list_entity_links
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain_membership import (
    DeclaredDomainMembership,
    STATUS_ACTIVE,
)
from vector.infrastructure.db.models.declared_domain import DeclaredDomain

_ARTIFACT_TYPES = ("work_item", "pull_request", "document", "deployment")


def list_work_artifacts(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    entity_type: str | None = None,
    connector: str | None = None,
    domain_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    types = (entity_type,) if entity_type else _ARTIFACT_TYPES
    filters = [
        CanonEntity.tenant_id == tenant_id,
        CanonEntity.entity_type.in_(types),
    ]
    if connector:
        filters.append(CanonEntity.connector == connector)
    if domain_id is not None:
        member_subq = (
            select(DeclaredDomainMembership.canon_entity_id)
            .where(
                DeclaredDomainMembership.tenant_id == tenant_id,
                DeclaredDomainMembership.declared_domain_id == domain_id,
                DeclaredDomainMembership.status == STATUS_ACTIVE,
            )
            .distinct()
        )
        filters.append(CanonEntity.id.in_(member_subq))

    total = int(session.scalar(select(func.count()).select_from(CanonEntity).where(*filters)) or 0)
    stmt = select(CanonEntity).where(*filters)
    rows = list(
        session.scalars(
            stmt.order_by(CanonEntity.materialized_at.desc()).offset(offset).limit(limit),
        ).all(),
    )
    labels = enrich_notion_display_labels(session, rows)
    items = [
        {
            "canon_entity_id": str(row.id),
            "entity_type": row.entity_type,
            "connector": row.connector,
            "display_label": labels.get(row.id, row.display_label),
            "materialized_at": row.materialized_at.isoformat(),
            "provider_status": _provider_status(row),
        }
        for row in rows
    ]
    return items, total


def _provider_status(entity: CanonEntity) -> str | None:
    attrs = entity.attrs_json if isinstance(entity.attrs_json, dict) else {}
    for key in ("state", "status", "workflow_state"):
        if key in attrs:
            return str(attrs[key])
    return None


def get_work_artifact_detail(
    session: Session,
    tenant_id: uuid.UUID,
    canon_entity_id: uuid.UUID,
) -> dict[str, Any] | None:
    entity = session.get(CanonEntity, canon_entity_id)
    if entity is None or entity.tenant_id != tenant_id:
        return None
    if entity.entity_type not in _ARTIFACT_TYPES:
        return None

    labels = enrich_notion_display_labels(session, [entity])
    links_payload = list_entity_links(session, tenant_id, canon_entity_id, limit=80)

    domain_rows = list(
        session.execute(
            select(DeclaredDomainMembership, DeclaredDomain)
            .join(DeclaredDomain, DeclaredDomain.id == DeclaredDomainMembership.declared_domain_id)
            .where(
                DeclaredDomainMembership.tenant_id == tenant_id,
                DeclaredDomainMembership.canon_entity_id == canon_entity_id,
                DeclaredDomainMembership.status == STATUS_ACTIVE,
            ),
        ).all(),
    )
    domains = [
        {
            "id": str(domain.id),
            "display_name": domain.display_name,
            "membership": {
                "extractor_rule": membership.extractor_rule,
                "expansion_level": membership.expansion_level,
                "evidence_ref": membership.evidence_ref,
            },
        }
        for membership, domain in domain_rows
    ]

    discussions: list[dict[str, Any]] = []
    for edge in links_payload.get("outbound", []) + links_payload.get("inbound", []):
        if edge.get("relationship_kind") in ("comments_on", "attached_to", "replies_to"):
            target = edge.get("to") or edge.get("from")
            if target:
                discussions.append(
                    {
                        "relationship_kind": edge["relationship_kind"],
                        "relationship_kind_label": edge.get("relationship_kind_label"),
                        "peer": target,
                        "extractor_rule": edge.get("extractor_rule"),
                        "observed_at": edge.get("observed_at"),
                    },
                )

    return {
        "entity": {
            "canon_entity_id": str(entity.id),
            "entity_type": entity.entity_type,
            "connector": entity.connector,
            "display_label": labels.get(entity.id, entity.display_label),
            "entity_key": entity.entity_key,
            "attrs_json": entity.attrs_json or {},
            "provider_status": _provider_status(entity),
            "materialized_at": entity.materialized_at.isoformat(),
        },
        "people": {
            "author_entity_id": str(entity.author_entity_id) if entity.author_entity_id else None,
            "assignee_entity_id": str(entity.assignee_entity_id) if entity.assignee_entity_id else None,
        },
        "connected_artifacts": {
            "outbound": links_payload.get("outbound", []),
            "inbound": links_payload.get("inbound", []),
        },
        "discussions": with_items(
            section(
                count=len(discussions),
                empty_code="no_discussion_links",
                empty_message="No discussion links on graph for this artifact.",
                empty_remediation="Improve graph comments_on / attached_to extraction.",
            ),
            discussions,
        ),
        "domain_memberships": domains,
        "activity": {
            "execution_timeline_available": False,
            "observation_signals": [],
            "footnote": "Artifact detail shows graph links only; operational timeline not canonized.",
        },
    }
