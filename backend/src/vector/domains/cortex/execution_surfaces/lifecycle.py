"""Deterministic lifecycle buckets for declared domains (provider status + observation)."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.canon.lifecycle_substrate import (
    LIFECYCLE_PHASE_ACTIVE,
    LIFECYCLE_PHASE_ARCHIVED,
    LIFECYCLE_PHASE_COMPLETED,
    LIFECYCLE_PHASE_DORMANT,
    LIFECYCLE_PHASE_PLANNED,
    LIFECYCLE_PHASE_UNKNOWN,
    derive_lifecycle_phase,
)
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain_stats import DeclaredDomainStats

# Backward-compatible aliases
LIFECYCLE_ACTIVE = LIFECYCLE_PHASE_ACTIVE
LIFECYCLE_PLANNED = LIFECYCLE_PHASE_PLANNED
LIFECYCLE_COMPLETED = LIFECYCLE_PHASE_COMPLETED
LIFECYCLE_DORMANT = LIFECYCLE_PHASE_DORMANT
LIFECYCLE_UNKNOWN = LIFECYCLE_PHASE_UNKNOWN


def lifecycle_bucket_for_domain(
    *,
    seed_entity: CanonEntity | None,
    stats: DeclaredDomainStats | None,
    events_30d: int | None = None,
) -> str:
    """Classify domain without inferring health or risk."""
    if seed_entity is not None and isinstance(seed_entity.attrs_json, dict):
        explicit = seed_entity.attrs_json.get("lifecycle_phase")
        if isinstance(explicit, str) and explicit:
            if explicit == LIFECYCLE_PHASE_ARCHIVED:
                return LIFECYCLE_DORMANT
            return explicit

    events_7d = stats.events_7d if stats is not None else 0
    mass = stats.mass_total if stats is not None else 0

    if seed_entity is not None and isinstance(seed_entity.attrs_json, dict):
        derived = derive_lifecycle_phase(seed_entity.attrs_json)
        if derived == LIFECYCLE_PHASE_COMPLETED:
            return LIFECYCLE_COMPLETED
        if derived == LIFECYCLE_PHASE_ARCHIVED:
            return LIFECYCLE_DORMANT
        if derived == LIFECYCLE_PHASE_PLANNED and events_7d == 0:
            return LIFECYCLE_PLANNED
        if derived == LIFECYCLE_PHASE_ACTIVE:
            return LIFECYCLE_ACTIVE

    if events_7d > 0:
        return LIFECYCLE_ACTIVE

    if events_30d is None:
        if events_7d == 0 and mass > 0:
            return LIFECYCLE_DORMANT
    elif events_30d == 0 and mass > 0:
        return LIFECYCLE_DORMANT

    if seed_entity is not None and isinstance(seed_entity.attrs_json, dict):
        derived = derive_lifecycle_phase(seed_entity.attrs_json)
        if derived == LIFECYCLE_PHASE_PLANNED:
            return LIFECYCLE_PLANNED
    return LIFECYCLE_UNKNOWN


def compute_events_30d_placeholder(stats: DeclaredDomainStats | None) -> int:
    """Use observation 7d + prior 7d as lower bound when 30d not stored."""
    if stats is None:
        return 0
    return stats.events_7d + stats.events_prior_7d


def domain_list_item_with_lifecycle(
  item: dict[str, Any],
  *,
  seed_entity: CanonEntity | None,
  stats: DeclaredDomainStats | None,
) -> dict[str, Any]:
    events_30d_proxy = compute_events_30d_placeholder(stats)
    bucket = lifecycle_bucket_for_domain(
        seed_entity=seed_entity,
        stats=stats,
        events_30d=events_30d_proxy if events_30d_proxy > 0 or (stats and stats.mass_total > 0) else 0,
    )
    out = dict(item)
    out["lifecycle_bucket"] = bucket
    return out


def matches_lifecycle_filter(bucket: str, lifecycle: str | None) -> bool:
    if not lifecycle or lifecycle == "all":
        return True
    return bucket == lifecycle
