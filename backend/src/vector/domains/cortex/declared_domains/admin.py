"""Admin-facing declared domains read APIs."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.declared_domains.extractor_version import (
    DECLARED_DOMAIN_EXTRACTOR_VERSION,
    effective_declared_domain_extractor_version,
)
from vector.domains.cortex.declared_domains.materialize import tenant_has_graph_backlog
from vector.domains.cortex.declared_domains.pass_run_ops import (
    abandon_stuck_running_declared_domain_passes,
    latest_declared_domain_pass_run,
)
from vector.domains.cortex.declared_domains.stats import recompute_domain_stats, sort_domains
from vector.domains.cortex.canon.notion_display_labels import enrich_notion_display_labels
from vector.domains.cortex.canon.notion_work_containers import list_notion_canon_databases
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain import DeclaredDomain
from vector.infrastructure.db.models.declared_domain_dirty_queue import DeclaredDomainDirtyQueue
from vector.infrastructure.db.models.declared_domain_membership import (
    DeclaredDomainMembership,
    STATUS_ACTIVE,
)
from vector.infrastructure.db.models.declared_domain_pass_run import DeclaredDomainPassRun
from vector.infrastructure.db.models.declared_domain_stats import DeclaredDomainStats
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.repositories import notion_connection as notion_repo

MANUAL_DECLARED_DOMAIN_PASS_CONFIRMATION = "RUN DECLARED DOMAIN PASS"


def _membership_summary(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    domain_id: uuid.UUID,
) -> dict[str, Any]:
    rows = session.execute(
        select(
            DeclaredDomainMembership.expansion_level,
            DeclaredDomainMembership.extractor_rule,
            func.count(),
        )
        .where(
            DeclaredDomainMembership.tenant_id == tenant_id,
            DeclaredDomainMembership.declared_domain_id == domain_id,
            DeclaredDomainMembership.status == STATUS_ACTIVE,
        )
        .group_by(
            DeclaredDomainMembership.expansion_level,
            DeclaredDomainMembership.extractor_rule,
        ),
    ).all()
    direct = 0
    graph = 0
    by_rule: dict[str, int] = {}
    for expansion_level, rule, count in rows:
        if expansion_level == "direct":
            direct += int(count)
        elif expansion_level == "graph":
            graph += int(count)
        by_rule[str(rule)] = int(count)
    return {
        "total": direct + graph,
        "direct": direct,
        "graph": graph,
        "by_rule": by_rule,
    }


def _notion_pin_summaries(session: Session, *, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    items = list_notion_canon_databases(session, tenant_id=tenant_id)
    return [
        {
            "database_id": item["database_id"],
            "display_name": item["display_name"],
            "row_count": item["row_count"],
            "is_pinned": item["is_pinned"],
            "is_declared_seed": item["is_declared_seed"],
        }
        for item in items
        if item["is_pinned"]
    ]


def _operational_status(
    *,
    domain_count: int,
    active_membership_count: int,
    work_container_pin_count: int,
    dirty_queue_pending: int,
    latest_pass_status: str | None,
) -> str:
    if domain_count == 0:
        if work_container_pin_count > 0 or dirty_queue_pending > 0:
            return "processing"
        return "needs_setup"
    if active_membership_count == 0:
        return "processing"
    if dirty_queue_pending > 0:
        return "catching_up"
    if latest_pass_status == "FAILED":
        return "failed"
    return "healthy"


def _tenant_has_active_connection(session: Session, tenant_id: uuid.UUID, provider: str) -> bool:
    found = session.scalar(
        select(TenantConnection.id)
        .where(
            TenantConnection.tenant_id == tenant_id,
            TenantConnection.provider == provider,
            TenantConnection.status == "active",
        )
        .limit(1),
    )
    return found is not None


def _empty_state_hint(
    *,
    domain_count: int,
    notion_connected: bool,
    linear_connected: bool,
    work_container_pin_count: int,
) -> str | None:
    if domain_count > 0:
        return None
    if notion_connected and not linear_connected and work_container_pin_count == 0:
        return (
            "No declared work containers yet. Pin one or more Notion databases as work "
            "containers in Integrations → Notion, then run a declared domain pass."
        )
    if linear_connected:
        return (
            "No declared domains yet. Ensure Linear initiatives or projects are materialized "
            "in Canon, then run a declared domain pass."
        )
    if notion_connected and work_container_pin_count > 0:
        return "Work databases are pinned. Run a declared domain pass to materialize domains."
    return "No declared work containers in canon. Connect Linear or pin Notion work databases."


def prepare_declared_domain_pass_trigger(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    interval_seconds: int,
) -> None:
    abandon_stuck_running_declared_domain_passes(
        session,
        tenant_id=tenant_id,
        interval_seconds=interval_seconds,
    )


def build_declared_domain_readiness(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    scheduler: dict[str, Any] | None = None,
    batch_entity_limit: int,
    activity_min_events: int,
    momentum_min_baseline: int,
) -> dict[str, Any]:
    dirty_pending = int(
        session.scalar(
            select(func.count())
            .select_from(DeclaredDomainDirtyQueue)
            .where(
                DeclaredDomainDirtyQueue.tenant_id == tenant_id,
                DeclaredDomainDirtyQueue.processed_at.is_(None),
            ),
        )
        or 0,
    )
    domain_count = int(
        session.scalar(
            select(func.count())
            .select_from(DeclaredDomain)
            .where(DeclaredDomain.tenant_id == tenant_id),
        )
        or 0,
    )
    active_memberships = int(
        session.scalar(
            select(func.count())
            .select_from(DeclaredDomainMembership)
            .where(
                DeclaredDomainMembership.tenant_id == tenant_id,
                DeclaredDomainMembership.status == STATUS_ACTIVE,
            ),
        )
        or 0,
    )
    latest = latest_declared_domain_pass_run(session, tenant_id=tenant_id)
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
    dirty_by_reason_rows = session.execute(
        select(DeclaredDomainDirtyQueue.reason, func.count())
        .where(
            DeclaredDomainDirtyQueue.tenant_id == tenant_id,
            DeclaredDomainDirtyQueue.processed_at.is_(None),
        )
        .group_by(DeclaredDomainDirtyQueue.reason),
    ).all()
    dirty_by_reason = {str(reason): int(count) for reason, count in dirty_by_reason_rows}
    graph_behind = tenant_has_graph_backlog(session, tenant_id)
    notion_connected = _tenant_has_active_connection(session, tenant_id, "notion")
    linear_connected = _tenant_has_active_connection(session, tenant_id, "linear")
    notion_link = notion_repo.get_notion_connection_for_tenant(session, tenant_id)
    from vector.domains.cortex.canon.notion_work_containers import pinned_database_ids

    work_container_pin_count = (
        len(pinned_database_ids(notion_link.detail.work_container_pins))
        if notion_link is not None
        else 0
    )
    empty_state_hint = _empty_state_hint(
        domain_count=domain_count,
        notion_connected=notion_connected,
        linear_connected=linear_connected,
        work_container_pin_count=work_container_pin_count,
    )
    operational_status = _operational_status(
        domain_count=domain_count,
        active_membership_count=active_memberships,
        work_container_pin_count=work_container_pin_count,
        dirty_queue_pending=dirty_pending,
        latest_pass_status=latest.status if latest is not None else None,
    )
    notion_pins = _notion_pin_summaries(session, tenant_id=tenant_id) if notion_connected else []
    active_domains = int(
        session.scalar(
            select(func.count())
            .select_from(DeclaredDomainStats)
            .where(
                DeclaredDomainStats.tenant_id == tenant_id,
                DeclaredDomainStats.events_7d > 0,
            ),
        )
        or 0,
    )
    return {
        "tenant_id": str(tenant_id),
        "extractor_version": effective_declared_domain_extractor_version(None),
        "extractor_version_code": DECLARED_DOMAIN_EXTRACTOR_VERSION,
        "batch_entity_limit": batch_entity_limit,
        "activity_min_events": activity_min_events,
        "momentum_min_baseline": momentum_min_baseline,
        "dirty_queue_pending": dirty_pending,
        "dirty_queue_by_reason": dirty_by_reason,
        "declared_domain_count": domain_count,
        "active_membership_count": active_memberships,
        "active_domain_count": active_domains,
        "graph_behind": graph_behind,
        "level0_available": domain_count > 0,
        "level1_advisory": graph_behind,
        "notion_connected": notion_connected,
        "linear_connected": linear_connected,
        "work_container_pin_count": work_container_pin_count,
        "notion_pins": notion_pins,
        "operational_status": operational_status,
        "empty_state_hint": empty_state_hint,
        "latest_pass_run": latest_payload,
        "scheduler": scheduler or {},
    }


def list_declared_domains(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    sort: str = "mass",
    activity_min_events: int,
    momentum_min_baseline: int,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    domains = list(
        session.scalars(select(DeclaredDomain).where(DeclaredDomain.tenant_id == tenant_id)).all(),
    )
    stats_by_domain: dict[uuid.UUID, DeclaredDomainStats] = {}
    if domains:
        stats_rows = session.scalars(
            select(DeclaredDomainStats).where(
                DeclaredDomainStats.tenant_id == tenant_id,
                DeclaredDomainStats.declared_domain_id.in_([d.id for d in domains]),
            ),
        ).all()
        stats_by_domain = {row.declared_domain_id: row for row in stats_rows}

    pairs = [(d, stats_by_domain.get(d.id)) for d in domains]
    sorted_pairs = sort_domains(
        pairs,
        sort=sort,
        activity_min_events=activity_min_events,
        momentum_min_baseline=momentum_min_baseline,
    )
    total = len(sorted_pairs)
    page = sorted_pairs[offset : offset + limit]
    seed_entities = session.scalars(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.id.in_([domain.seed_canon_entity_id for domain, _ in page]),
        ),
    ).all()
    seed_labels = enrich_notion_display_labels(session, seed_entities)
    seed_by_id = {entity.id: entity for entity in seed_entities}
    items: list[dict[str, Any]] = []
    for domain, stats in page:
        seed_entity = seed_by_id.get(domain.seed_canon_entity_id)
        display_name = (
            seed_labels.get(seed_entity.id, seed_entity.display_label)
            if seed_entity is not None
            else domain.display_name
        )
        membership_summary = _membership_summary(session, tenant_id=tenant_id, domain_id=domain.id)
        items.append(
            {
                "id": str(domain.id),
                "display_name": display_name,
                "declared_container_kind": domain.declared_container_kind,
                "seed_connector": domain.seed_connector,
                "seed_resource_type": domain.seed_resource_type,
                "seed_canon_entity_id": str(domain.seed_canon_entity_id),
                "active_membership_count": membership_summary["total"],
                "membership_summary": membership_summary,
                "first_observed_at": domain.first_observed_at.isoformat(),
                "last_activity_at": domain.last_activity_at.isoformat()
                if domain.last_activity_at
                else None,
                "stats": _stats_payload(stats),
            },
        )
    return items, total


def get_declared_domain_detail(
    session: Session,
    tenant_id: uuid.UUID,
    domain_id: uuid.UUID,
    *,
    membership_limit: int = 100,
) -> dict[str, Any] | None:
    domain = session.get(DeclaredDomain, domain_id)
    if domain is None or domain.tenant_id != tenant_id:
        return None
    stats = session.get(DeclaredDomainStats, domain.id)
    if stats is not None and stats.mass_total == 0:
        pending_members = int(
            session.scalar(
                select(func.count())
                .select_from(DeclaredDomainMembership)
                .where(
                    DeclaredDomainMembership.tenant_id == tenant_id,
                    DeclaredDomainMembership.declared_domain_id == domain.id,
                    DeclaredDomainMembership.status == STATUS_ACTIVE,
                ),
            )
            or 0,
        )
        if pending_members > 0:
            stats = recompute_domain_stats(
                session,
                tenant_id=tenant_id,
                domain=domain,
                expansion_level=stats.expansion_level or "direct",
                momentum_min_baseline=5,
            )
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
    member_entities: dict[uuid.UUID, CanonEntity] = {}
    if memberships:
        entity_ids = [m.canon_entity_id for m in memberships]
        rows = session.scalars(
            select(CanonEntity).where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.id.in_(entity_ids),
            ),
        ).all()
        member_entities = {row.id: row for row in rows}

    labels = enrich_notion_display_labels(session, member_entities.values())
    seed_entity = session.get(CanonEntity, domain.seed_canon_entity_id)
    seed_labels = enrich_notion_display_labels(session, [seed_entity]) if seed_entity else {}
    display_name = (
        seed_labels.get(seed_entity.id, seed_entity.display_label)
        if seed_entity is not None
        else domain.display_name
    )
    membership_summary = _membership_summary(session, tenant_id=tenant_id, domain_id=domain.id)

    membership_payload = []
    for membership in memberships:
        entity = member_entities.get(membership.canon_entity_id)
        resource_type = None
        if entity is not None:
            parts = entity.entity_key.split(":")
            if len(parts) >= 3:
                resource_type = parts[2]
        membership_payload.append(
            {
                "id": str(membership.id),
                "canon_entity_id": str(membership.canon_entity_id),
                "entity_type": entity.entity_type if entity else None,
                "resource_type": resource_type,
                "connector": entity.connector if entity else None,
                "display_label": labels.get(entity.id, entity.display_label) if entity else None,
                "extractor_rule": membership.extractor_rule,
                "expansion_level": membership.expansion_level,
                "evidence_kind": membership.evidence_kind,
                "evidence_ref": membership.evidence_ref,
                "seed_distance": membership.seed_distance,
                "observed_at": membership.observed_at.isoformat(),
            },
        )
    return {
        "id": str(domain.id),
        "display_name": display_name,
        "declared_container_kind": domain.declared_container_kind,
        "seed_connector": domain.seed_connector,
        "seed_resource_type": domain.seed_resource_type,
        "seed_canon_entity_id": str(domain.seed_canon_entity_id),
        "stats": _stats_payload(stats),
        "membership_summary": membership_summary,
        "memberships": membership_payload,
    }


def list_declared_domain_pass_runs(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    total = int(
        session.scalar(
            select(func.count())
            .select_from(DeclaredDomainPassRun)
            .where(DeclaredDomainPassRun.tenant_id == tenant_id),
        )
        or 0,
    )
    rows = list(
        session.scalars(
            select(DeclaredDomainPassRun)
            .where(DeclaredDomainPassRun.tenant_id == tenant_id)
            .order_by(DeclaredDomainPassRun.started_at.desc())
            .offset(offset)
            .limit(limit),
        ).all(),
    )
    items = [
        {
            "id": str(row.id),
            "status": row.status,
            "source_trigger": row.source_trigger,
            "started_at": row.started_at.isoformat(),
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            "stats": row.stats or {},
            "error_summary": row.error_summary,
        }
        for row in rows
    ]
    return items, total


def _stats_payload(stats: DeclaredDomainStats | None) -> dict[str, Any]:
    if stats is None:
        return {
            "artifact_counts_json": {},
            "participant_count": 0,
            "events_7d": 0,
            "events_prior_7d": 0,
            "activity_delta_7d": 0,
            "momentum_pct": None,
            "mass_total": 0,
            "expansion_level": "direct",
            "computed_at": None,
        }
    return {
        "artifact_counts_json": stats.artifact_counts_json or {},
        "participant_count": stats.participant_count,
        "events_7d": stats.events_7d,
        "events_prior_7d": stats.events_prior_7d,
        "activity_delta_7d": stats.activity_delta_7d,
        "momentum_pct": float(stats.momentum_pct) if stats.momentum_pct is not None else None,
        "mass_total": stats.mass_total,
        "expansion_level": stats.expansion_level,
        "computed_at": stats.computed_at.isoformat(),
    }
