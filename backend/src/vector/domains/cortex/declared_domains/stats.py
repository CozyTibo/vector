"""Declared domain stats rollup."""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.domains.cortex.declared_domains.mass import mass_for_entity_type
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain import DeclaredDomain
from vector.infrastructure.db.models.declared_domain_membership import (
    DeclaredDomainMembership,
    STATUS_ACTIVE,
)
from vector.infrastructure.db.models.declared_domain_stats import (
    DeclaredDomainStats,
    EXPANSION_DIRECT,
)


def _activity_at(entity: CanonEntity):
    return entity.materialized_at


def _count_events_in_window(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    declared_domain_id: uuid.UUID,
    start,
    end,
) -> int:
    return int(
        session.scalar(
            select(func.count(func.distinct(CanonEntity.id)))
            .select_from(DeclaredDomainMembership)
            .join(CanonEntity, CanonEntity.id == DeclaredDomainMembership.canon_entity_id)
            .where(
                DeclaredDomainMembership.tenant_id == tenant_id,
                DeclaredDomainMembership.declared_domain_id == declared_domain_id,
                DeclaredDomainMembership.status == STATUS_ACTIVE,
                CanonEntity.materialized_at > start,
                CanonEntity.materialized_at <= end,
            ),
        )
        or 0,
    )


def recompute_domain_stats(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    domain: DeclaredDomain,
    expansion_level: str,
    momentum_min_baseline: int,
) -> DeclaredDomainStats:
    now = utc_now()
    window_end = now
    window_7d_start = now - timedelta(days=7)
    window_prior_start = now - timedelta(days=14)

    memberships = list(
        session.scalars(
            select(DeclaredDomainMembership)
            .where(
                DeclaredDomainMembership.tenant_id == tenant_id,
                DeclaredDomainMembership.declared_domain_id == domain.id,
                DeclaredDomainMembership.status == STATUS_ACTIVE,
            ),
        ).all(),
    )
    member_ids = [m.canon_entity_id for m in memberships]
    entities: list[CanonEntity] = []
    if member_ids:
        entities = list(
            session.scalars(
                select(CanonEntity).where(
                    CanonEntity.tenant_id == tenant_id,
                    CanonEntity.id.in_(member_ids),
                ),
            ).all(),
        )

    artifact_counts: dict[str, int] = {}
    mass_total = 0
    participant_ids: set[uuid.UUID] = set()
    last_activity_at = domain.last_activity_at

    for entity in entities:
        artifact_counts[entity.entity_type] = artifact_counts.get(entity.entity_type, 0) + 1
        mass_total += mass_for_entity_type(entity.entity_type)
        activity = _activity_at(entity)
        if activity is not None and (last_activity_at is None or activity > last_activity_at):
            last_activity_at = activity
        for fk in (
            entity.author_entity_id,
            entity.assignee_entity_id,
        ):
            if fk is not None:
                participant_ids.add(fk)

    events_7d = _count_events_in_window(
        session,
        tenant_id=tenant_id,
        declared_domain_id=domain.id,
        start=window_7d_start,
        end=window_end,
    )
    events_prior_7d = _count_events_in_window(
        session,
        tenant_id=tenant_id,
        declared_domain_id=domain.id,
        start=window_prior_start,
        end=window_7d_start,
    )
    activity_delta_7d = events_7d - events_prior_7d
    momentum_pct: Decimal | None = None
    if events_prior_7d >= momentum_min_baseline:
        pct = (Decimal(activity_delta_7d) / Decimal(max(events_prior_7d, 1))) * Decimal(100)
        momentum_pct = pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    stats = session.get(DeclaredDomainStats, domain.id)
    if stats is None:
        stats = DeclaredDomainStats(
            declared_domain_id=domain.id,
            tenant_id=tenant_id,
        )
        session.add(stats)

    stats.artifact_counts_json = artifact_counts
    stats.participant_count = len(participant_ids)
    stats.events_7d = events_7d
    stats.events_prior_7d = events_prior_7d
    stats.activity_delta_7d = activity_delta_7d
    stats.momentum_pct = momentum_pct
    stats.mass_total = mass_total
    stats.expansion_level = expansion_level or EXPANSION_DIRECT
    stats.computed_at = now

    domain.last_activity_at = last_activity_at
    domain.updated_at = now
    session.flush()
    return stats


SORT_MASS = "mass"
SORT_ACTIVITY = "activity"
SORT_GROWING = "growing"
SORT_SHRINKING = "shrinking"
SORT_NAME = "name"


def sort_domains(
    domains: list[tuple[DeclaredDomain, DeclaredDomainStats | None]],
    *,
    sort: str,
    activity_min_events: int,
    momentum_min_baseline: int,
) -> list[tuple[DeclaredDomain, DeclaredDomainStats | None]]:
    if sort == SORT_NAME:
        return sorted(domains, key=lambda pair: pair[0].display_name.lower())

    def stats_or_default(pair: tuple[DeclaredDomain, DeclaredDomainStats | None]) -> DeclaredDomainStats:
        _, stats = pair
        if stats is not None:
            return stats
        return DeclaredDomainStats(
            declared_domain_id=pair[0].id,
            tenant_id=pair[0].tenant_id,
            artifact_counts_json={},
            computed_at=utc_now(),
        )

    if sort == SORT_ACTIVITY:
        return sorted(
            domains,
            key=lambda pair: stats_or_default(pair).events_7d,
            reverse=True,
        )
    if sort == SORT_GROWING:
        filtered = [
            pair
            for pair in domains
            if stats_or_default(pair).events_7d >= activity_min_events
            and stats_or_default(pair).events_prior_7d >= momentum_min_baseline
        ]
        return sorted(
            filtered,
            key=lambda pair: stats_or_default(pair).activity_delta_7d,
            reverse=True,
        )
    if sort == SORT_SHRINKING:
        filtered = [
            pair
            for pair in domains
            if stats_or_default(pair).events_prior_7d >= momentum_min_baseline
        ]
        return sorted(filtered, key=lambda pair: stats_or_default(pair).activity_delta_7d)
    return sorted(
        domains,
        key=lambda pair: stats_or_default(pair).mass_total,
        reverse=True,
    )
