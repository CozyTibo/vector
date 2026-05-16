"""Graph construction completeness (org graph linkage accounting)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, union_all
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1, pct
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate


def _count_entities_with_authoritative_links(session: Session, *, tenant_id: uuid.UUID) -> int:
    src = select(CortexOrgLink.source_entity_id.label("entity_id")).where(
        CortexOrgLink.tenant_id == tenant_id,
        CortexOrgLink.revoked_at.is_(None),
    )
    tgt = select(CortexOrgLink.target_entity_id.label("entity_id")).where(
        CortexOrgLink.tenant_id == tenant_id,
        CortexOrgLink.revoked_at.is_(None),
    )
    linked = union_all(src, tgt).subquery()
    return int(
        session.scalar(select(func.count(func.distinct(linked.c.entity_id)))) or 0
    )


def project_graph_completeness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    entity_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(CortexOrgEntity.tenant_id == tenant_id)
        )
        or 0
    )
    link_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.revoked_at.is_(None),
            )
        )
        or 0
    )
    candidate_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLinkCandidate)
            .where(CortexOrgLinkCandidate.tenant_id == tenant_id)
        )
        or 0
    )
    linked_entities = _count_entities_with_authoritative_links(session, tenant_id=tenant_id)
    orphan_count = max(0, entity_count - linked_entities)

    omission_classes: dict[str, int] = {}
    if orphan_count:
        omission_classes["orphan_artifacts"] = orphan_count
    pending_candidates = max(0, candidate_count - link_count)
    if pending_candidates > 0:
        omission_classes["pending_link_candidates"] = pending_candidates

    substrate_state = "healthy"
    if entity_count == 0:
        substrate_state = "critical"
    elif orphan_count > entity_count * 0.2:
        substrate_state = "degraded"
    elif link_count == 0 and candidate_count > 0:
        substrate_state = "degraded"

    replay_posture = "stable" if linked_entities and not orphan_count else (
        "partial" if linked_entities else "unknown"
    )

    return build_stage_envelope_v1(
        stage_id="graph",
        label="Graph",
        total_objects=entity_count,
        processed_count=linked_entities,
        degraded_count=0,
        unresolved_count=orphan_count,
        omitted_count=pending_candidates,
        replay_posture=replay_posture,
        substrate_state=substrate_state,
        omission_classes=omission_classes,
        detail_route=f"/admin/tenants/{tenant_id}/cortex/graph",
        metrics={
            "entity_count": entity_count,
            "linked_entity_count": linked_entities,
            "authoritative_link_count": link_count,
            "candidate_link_count": candidate_count,
            "graph_connectivity_percent": pct(linked_entities, entity_count if entity_count else 1),
            "orphan_node_count": orphan_count,
        },
    )
