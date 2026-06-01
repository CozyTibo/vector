"""Declared domain composition for Execution Surfaces."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.notion_display_labels import enrich_notion_display_labels
from vector.domains.cortex.declared_domains.admin import list_declared_domains
from vector.domains.cortex.execution_surfaces.connected_work import build_connected_work
from vector.domains.cortex.execution_surfaces.lifecycle import (
    domain_list_item_with_lifecycle,
    matches_lifecycle_filter,
)
from vector.domains.cortex.execution_surfaces.context import build_substrate_context
from vector.domains.cortex.execution_surfaces.omissions import (
    EXECUTION_ACTIVITY_UNAVAILABLE_FOOTNOTE,
    OBSERVATION_ACTIVITY_FOOTNOTE,
    section,
    with_items,
)
from vector.domains.cortex.graph.relationship_kinds import label_for_kind
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain import DeclaredDomain
from vector.infrastructure.db.models.declared_domain_membership import (
    DeclaredDomainMembership,
    STATUS_ACTIVE,
)
from vector.infrastructure.db.models.declared_domain_stats import DeclaredDomainStats
from vector.infrastructure.db.models.graph_relationship import STATUS_ACTIVE as GRAPH_ACTIVE
from vector.infrastructure.db.models.graph_relationship import GraphRelationship
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_entity import IdentityEntity

_WORK_ITEM_TYPES = frozenset({"work_item"})
_PR_TYPES = frozenset({"pull_request"})
_DOC_TYPES = frozenset({"document"})
_DEPLOY_TYPES = frozenset({"deployment"})
_CONVERSATION_TYPES = frozenset({"message", "conversation"})


def _entity_ref(entity: CanonEntity, labels: dict[uuid.UUID, str]) -> dict[str, Any]:
    return {
        "canon_entity_id": str(entity.id),
        "entity_type": entity.entity_type,
        "connector": entity.connector,
        "display_label": labels.get(entity.id, entity.display_label),
        "entity_key": entity.entity_key,
        "attrs_json": entity.attrs_json or {},
    }


def _resolve_identities_for_actors(
    session: Session,
    tenant_id: uuid.UUID,
    actor_entity_ids: set[uuid.UUID],
) -> dict[uuid.UUID, dict[str, Any]]:
    if not actor_entity_ids:
        return {}
    rows = session.execute(
        select(IdentityAccount, IdentityEntity)
        .join(IdentityEntity, IdentityEntity.id == IdentityAccount.identity_entity_id)
        .where(
            IdentityAccount.tenant_id == tenant_id,
            IdentityAccount.canon_entity_id.in_(actor_entity_ids),
            IdentityAccount.unlinked_at.is_(None),
            IdentityEntity.status == "active",
        ),
    ).all()
    out: dict[uuid.UUID, dict[str, Any]] = {}
    for account, identity in rows:
        out[account.canon_entity_id] = {
            "identity_id": str(identity.id),
            "display_name": identity.display_name,
            "kind": identity.kind,
            "connectors": [account.connector],
        }
    return out


def list_domains_for_surface(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    sort: str = "activity",
    lifecycle: str | None = None,
    activity_min_events: int,
    momentum_min_baseline: int,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    items, _ = list_declared_domains(
        session,
        tenant_id,
        sort=sort,
        activity_min_events=activity_min_events,
        momentum_min_baseline=momentum_min_baseline,
        offset=0,
        limit=500,
    )
    seed_ids = [uuid.UUID(str(item["seed_canon_entity_id"])) for item in items]
    stats_by_domain: dict[uuid.UUID, DeclaredDomainStats] = {}
    domain_ids = [uuid.UUID(str(item["id"])) for item in items]
    if domain_ids:
        for stats_row in session.scalars(
            select(DeclaredDomainStats).where(
                DeclaredDomainStats.tenant_id == tenant_id,
                DeclaredDomainStats.declared_domain_id.in_(domain_ids),
            ),
        ).all():
            stats_by_domain[stats_row.declared_domain_id] = stats_row
    seeds: dict[uuid.UUID, CanonEntity] = {}
    if seed_ids:
        for seed in session.scalars(
            select(CanonEntity).where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.id.in_(seed_ids),
            ),
        ).all():
            seeds[seed.id] = seed

    enriched: list[dict[str, Any]] = []
    for item in items:
        domain_id = uuid.UUID(str(item["id"]))
        seed_id = uuid.UUID(str(item["seed_canon_entity_id"]))
        stats_row = stats_by_domain.get(domain_id)
        stats_dict = item.get("stats") or {}
        item["observation_stats"] = {
            "events_7d": stats_dict.get("events_7d", 0),
            "events_prior_7d": stats_dict.get("events_prior_7d", 0),
            "activity_delta_7d": stats_dict.get("activity_delta_7d", 0),
            "mass_total": stats_dict.get("mass_total", 0),
            "footnote": OBSERVATION_ACTIVITY_FOOTNOTE,
        }
        with_lifecycle = domain_list_item_with_lifecycle(
            item,
            seed_entity=seeds.get(seed_id),
            stats=stats_row,
        )
        if matches_lifecycle_filter(with_lifecycle["lifecycle_bucket"], lifecycle):
            enriched.append(with_lifecycle)

    total = len(enriched)
    page = enriched[offset : offset + limit]
    return page, total


def get_domain_surface_detail(
    session: Session,
    tenant_id: uuid.UUID,
    domain_id: uuid.UUID,
    *,
    membership_limit: int = 500,
) -> dict[str, Any] | None:
    domain = session.get(DeclaredDomain, domain_id)
    if domain is None or domain.tenant_id != tenant_id:
        return None

    stats = session.get(DeclaredDomainStats, domain.id)
    memberships = list(
        session.scalars(
            select(DeclaredDomainMembership)
            .where(
                DeclaredDomainMembership.tenant_id == tenant_id,
                DeclaredDomainMembership.declared_domain_id == domain.id,
                DeclaredDomainMembership.status == STATUS_ACTIVE,
            )
            .order_by(DeclaredDomainMembership.seed_distance.asc())
            .limit(membership_limit),
        ).all(),
    )
    member_ids = {m.canon_entity_id for m in memberships}
    entities: dict[uuid.UUID, CanonEntity] = {}
    if member_ids:
        for ent in session.scalars(
            select(CanonEntity).where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.id.in_(member_ids),
            ),
        ).all():
            entities[ent.id] = ent

    labels = enrich_notion_display_labels(session, entities.values())
    seed_entity = session.get(CanonEntity, domain.seed_canon_entity_id)
    seed_labels = enrich_notion_display_labels(session, [seed_entity]) if seed_entity else {}
    display_name = (
        seed_labels.get(seed_entity.id, seed_entity.display_label)
        if seed_entity is not None
        else domain.display_name
    )

    substrate = build_substrate_context(session, tenant_id)
    graph_incomplete = substrate["graph_expansion_incomplete"]

    work_items: list[dict[str, Any]] = []
    prs: list[dict[str, Any]] = []
    docs: list[dict[str, Any]] = []
    deploys: list[dict[str, Any]] = []
    conversations: list[dict[str, Any]] = []
    actor_ids: set[uuid.UUID] = set()

    for membership in memberships:
        entity = entities.get(membership.canon_entity_id)
        if entity is None:
            continue
        ref = _entity_ref(entity, labels)
        ref["membership"] = {
            "extractor_rule": membership.extractor_rule,
            "expansion_level": membership.expansion_level,
            "evidence_kind": membership.evidence_kind,
            "evidence_ref": membership.evidence_ref,
            "seed_distance": membership.seed_distance,
        }
        if entity.author_entity_id:
            actor_ids.add(entity.author_entity_id)
        if entity.assignee_entity_id:
            actor_ids.add(entity.assignee_entity_id)

        et = entity.entity_type
        if et in _WORK_ITEM_TYPES:
            work_items.append(ref)
        elif et in _PR_TYPES:
            prs.append(ref)
        elif et in _DOC_TYPES:
            docs.append(ref)
        elif et in _DEPLOY_TYPES:
            deploys.append(ref)
        elif et in _CONVERSATION_TYPES:
            conversations.append(ref)

    identity_by_actor = _resolve_identities_for_actors(session, tenant_id, actor_ids)
    owners: dict[str, dict[str, Any]] = {}
    participants: dict[str, dict[str, Any]] = {}
    for actor_id, ident in identity_by_actor.items():
        participants[ident["identity_id"]] = ident
    for entity in entities.values():
        if entity.assignee_entity_id and entity.assignee_entity_id in identity_by_actor:
            ident = identity_by_actor[entity.assignee_entity_id]
            owners[ident["identity_id"]] = {**ident, "via": "assignee"}
        if entity.author_entity_id and entity.author_entity_id in identity_by_actor:
            ident = identity_by_actor[entity.author_entity_id]
            participants[ident["identity_id"]] = ident

    # Graph relationships among members (for activity + evidence)
    graph_rows: list[GraphRelationship] = []
    if member_ids:
        graph_rows = list(
            session.scalars(
                select(GraphRelationship)
                .where(
                    GraphRelationship.tenant_id == tenant_id,
                    GraphRelationship.status == GRAPH_ACTIVE,
                    or_(
                        GraphRelationship.from_entity_id.in_(member_ids),
                        GraphRelationship.to_entity_id.in_(member_ids),
                    ),
                )
                .order_by(GraphRelationship.observed_at.desc())
                .limit(100),
            ).all(),
        )

    observation_signals: list[dict[str, Any]] = []
    for row in graph_rows[:40]:
        from_ent = entities.get(row.from_entity_id) or session.get(CanonEntity, row.from_entity_id)
        to_ent = entities.get(row.to_entity_id) or session.get(CanonEntity, row.to_entity_id)
        if from_ent is None or to_ent is None:
            continue
        observation_signals.append(
            {
                "observed_at": row.observed_at.isoformat(),
                "label": f"Relationship recorded: {label_for_kind(row.relationship_kind)}",
                "relationship_kind": row.relationship_kind,
                "from": _entity_ref(from_ent, labels),
                "to": _entity_ref(to_ent, labels),
                "provenance": {
                    "kind": "graph_relationship",
                    "id": str(row.id),
                    "extractor_rule": row.extractor_rule,
                    "evidence_kind": row.evidence_kind,
                    "evidence_ref": row.evidence_ref,
                    "confidence": row.confidence,
                },
            },
        )

    conv_section = with_items(
        section(
            count=len(conversations),
            empty_code="no_conversations_in_domain",
            empty_message="No Slack messages or conversations in domain membership.",
            empty_remediation="Improve graph expansion and references from issues/PRs to Slack threads.",
        ),
        conversations,
    )
    if graph_incomplete and len(conversations) == 0:
        conv_section["omission"] = {
            "code": "graph_expansion_incomplete",
            "message": "Cross-tool links unavailable. Graph expansion incomplete.",
            "remediation": "Drain graph dirty queue and re-run declared domain pass for Level 1 expansion.",
        }

    meetings_section = section(
        count=0,
        empty_code="calls_not_canonized",
        empty_message="Meetings not yet canonized.",
        empty_remediation="Canonize calls.meeting in canon layer (currently deferred).",
    )
    if substrate["calls_meeting_raw_count"] == 0:
        meetings_section = section(
            count=0,
            empty_code="no_calls_ingested",
            empty_message="No meeting records ingested for this tenant.",
            empty_remediation="Connect Calls connector and ingest meetings.",
        )

    connected = build_connected_work(session, tenant_id, member_ids)

    membership_evidence = [
        {
            "canon_entity_id": str(m.canon_entity_id),
            "display_label": labels.get(m.canon_entity_id, entities[m.canon_entity_id].display_label)
            if m.canon_entity_id in entities
            else None,
            "extractor_rule": m.extractor_rule,
            "expansion_level": m.expansion_level,
            "evidence_kind": m.evidence_kind,
            "evidence_ref": m.evidence_ref,
        }
        for m in memberships[:30]
    ]

    graph_evidence = [
        {
            "id": str(row.id),
            "relationship_kind": row.relationship_kind,
            "extractor_rule": row.extractor_rule,
            "evidence_ref": row.evidence_ref,
            "from_entity_id": str(row.from_entity_id),
            "to_entity_id": str(row.to_entity_id),
        }
        for row in graph_rows[:30]
    ]

    seed_status = None
    if seed_entity is not None and isinstance(seed_entity.attrs_json, dict):
        for key in ("state", "status", "workflow_state"):
            if key in seed_entity.attrs_json:
                seed_status = str(seed_entity.attrs_json[key])
                break

    stats_payload: dict[str, Any] = {}
    if stats is not None:
        stats_payload = {
            "artifact_counts_json": stats.artifact_counts_json or {},
            "participant_count": stats.participant_count,
            "observation_events_7d": stats.events_7d,
            "observation_events_prior_7d": stats.events_prior_7d,
            "observation_activity_delta_7d": stats.activity_delta_7d,
            "mass_total": stats.mass_total,
            "expansion_level": stats.expansion_level,
            "computed_at": stats.computed_at.isoformat(),
            "footnote": OBSERVATION_ACTIVITY_FOOTNOTE,
        }

    from vector.domains.cortex.execution_surfaces.lifecycle import lifecycle_bucket_for_domain

    lifecycle_bucket = lifecycle_bucket_for_domain(
        seed_entity=seed_entity,
        stats=stats,
        events_30d=(stats.events_7d + stats.events_prior_7d) if stats else 0,
    )

    return {
        "id": str(domain.id),
        "display_name": display_name,
        "lifecycle_bucket": lifecycle_bucket,
        "declared_container_kind": domain.declared_container_kind,
        "seed_connector": domain.seed_connector,
        "seed_resource_type": domain.seed_resource_type,
        "seed_canon_entity_id": str(domain.seed_canon_entity_id),
        "seed_provider_status": seed_status,
        "why_belong_together": (
            f"Artifacts are members because they match declared container rules "
            f"({domain.declared_container_kind}) at Level 0 (direct attributes) "
            f"and/or Level 1 (graph expansion from seed)."
        ),
        "summary": {
            "stats": stats_payload,
            "member_count": len(memberships),
            "substrate": substrate,
        },
        "current_work": {
            "work_items": with_items(
                section(
                    count=len(work_items),
                    empty_code="no_work_items",
                    empty_message="No work items in this domain.",
                    empty_remediation="Check Linear/GitHub linkage to declared container seed.",
                ),
                work_items,
            ),
            "pull_requests": with_items(
                section(
                    count=len(prs),
                    empty_code="no_pull_requests",
                    empty_message="No pull requests in this domain.",
                    empty_remediation="Improve graph references from issues/docs to PRs.",
                ),
                prs,
            ),
            "documents": with_items(
                section(
                    count=len(docs),
                    empty_code="no_documents",
                    empty_message="No documents in this domain.",
                    empty_remediation="Link Notion pages via graph references or direct membership.",
                ),
                docs,
            ),
            "deployments": with_items(
                section(
                    count=len(deploys),
                    empty_code="no_deployments",
                    empty_message="No deployments in this domain.",
                    empty_remediation="Ensure deployment canonization and graph deploys edges.",
                ),
                deploys,
            ),
        },
        "people": {
            "owners": list(owners.values()),
            "participants": list(participants.values()),
            "omission": None
            if participants
            else {
                "code": "no_resolved_participants",
                "message": "No identity-resolved participants on domain artifacts.",
                "remediation": "Run Identity pass and link actor canon entities.",
            },
        },
        "activity": {
            "execution_timeline_available": False,
            "footnote": EXECUTION_ACTIVITY_UNAVAILABLE_FOOTNOTE,
            "observation_signals": observation_signals,
            "observation_signal_count": len(observation_signals),
            "omission": {
                "code": "execution_timeline_not_available",
                "message": "Operational execution timeline is not canonized yet.",
                "remediation": "Future: canonize provider timeline events (PR merge, assignment, etc.).",
            }
            if not observation_signals
            else None,
        },
        "conversations": {
            "slack_and_threads": conv_section,
            "meetings": meetings_section,
        },
        "connected_work": connected,
        "evidence": {
            "membership_rules": membership_evidence,
            "graph_rules": graph_evidence,
        },
    }
