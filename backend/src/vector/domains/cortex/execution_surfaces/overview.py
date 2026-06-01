"""Overview page — secondary to domain detail."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution_surfaces.activity import list_observation_activity
from vector.domains.cortex.execution_surfaces.connected_work import build_connected_work
from vector.domains.cortex.execution_surfaces.context import build_substrate_context
from vector.domains.cortex.execution_surfaces.domains import list_domains_for_surface
from vector.domains.cortex.execution_surfaces.omissions import OBSERVATION_ACTIVITY_FOOTNOTE
from vector.domains.cortex.execution_surfaces.people import list_people_for_surface
from vector.infrastructure.db.models.declared_domain_membership import (
    DeclaredDomainMembership,
    STATUS_ACTIVE,
)


def _overview_connected_work_samples(
    session: Session,
    tenant_id: uuid.UUID,
    domain_items: list[dict[str, Any]],
) -> dict[str, Any]:
    chains: list[dict[str, Any]] = []
    for item in domain_items[:5]:
        domain_id = uuid.UUID(str(item["id"]))
        member_ids = set(
            session.scalars(
                select(DeclaredDomainMembership.canon_entity_id).where(
                    DeclaredDomainMembership.tenant_id == tenant_id,
                    DeclaredDomainMembership.declared_domain_id == domain_id,
                    DeclaredDomainMembership.status == STATUS_ACTIVE,
                ),
            ).all(),
        )
        result = build_connected_work(session, tenant_id, member_ids)
        for chain in result.get("chains") or []:
            chains.append(
                {
                    "domain_id": str(domain_id),
                    "domain_name": item.get("display_name"),
                    **chain,
                },
            )
        if len(chains) >= 5:
            break
    if not chains:
        return {
            "chains": [],
            "count": 0,
            "omission": {
                "code": "insufficient_cross_tool_links",
                "message": "No cross-tool chains available on overview.",
                "remediation": "Improve graph references and declared domain membership.",
            },
        }
    return {"chains": chains[:5], "count": min(len(chains), 5), "omission": None}


def build_overview(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    activity_min_events: int,
    momentum_min_baseline: int,
) -> dict[str, Any]:
    substrate = build_substrate_context(session, tenant_id)
    domains, _ = list_domains_for_surface(
        session,
        tenant_id,
        sort="activity",
        activity_min_events=activity_min_events,
        momentum_min_baseline=momentum_min_baseline,
        limit=8,
    )
    people, _ = list_people_for_surface(session, tenant_id, limit=8)
    people_sorted = sorted(
        people,
        key=lambda p: (
            (p.get("participation") or {}).get("work_items", 0)
            + (p.get("participation") or {}).get("messages", 0)
        ),
        reverse=True,
    )
    recent_activity, _, activity_meta = list_observation_activity(
        session,
        tenant_id,
        hours=168,
        limit=15,
        offset=0,
    )
    connected_work = _overview_connected_work_samples(session, tenant_id, domains)
    return {
        "substrate": substrate,
        "observation_footnote": OBSERVATION_ACTIVITY_FOOTNOTE,
        "active_domains": domains,
        "active_people": people_sorted,
        "recent_observation_activity": recent_activity,
        "activity_meta": activity_meta,
        "connected_work": connected_work,
        "hero_route_hint": "Open a declared domain for full execution context.",
    }
