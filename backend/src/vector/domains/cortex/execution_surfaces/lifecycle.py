"""Deterministic lifecycle buckets for declared domains (provider status + observation)."""

from __future__ import annotations

from typing import Any

from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain_stats import DeclaredDomainStats

# Provider status sets (extend per connector in registry later)
LINEAR_COMPLETED = frozenset({"completed", "done", "canceled", "cancelled"})
LINEAR_PLANNED = frozenset({"planned", "backlog", "triage", "unstarted"})
LINEAR_ACTIVE = frozenset({"started", "in progress", "in_progress", "active"})

LIFECYCLE_ACTIVE = "active"
LIFECYCLE_PLANNED = "planned"
LIFECYCLE_COMPLETED = "completed"
LIFECYCLE_DORMANT = "dormant"
LIFECYCLE_UNKNOWN = "unknown"


def _normalize_status(raw: object) -> str | None:
    if raw is None:
        return None
    return str(raw).strip().lower()


def lifecycle_bucket_for_domain(
    *,
    seed_entity: CanonEntity | None,
    stats: DeclaredDomainStats | None,
    events_30d: int | None = None,
) -> str:
    """Classify domain without inferring health or risk."""
    status: str | None = None
    if seed_entity is not None and isinstance(seed_entity.attrs_json, dict):
        for key in ("state", "status", "workflow_state"):
            if key in seed_entity.attrs_json:
                status = _normalize_status(seed_entity.attrs_json[key])
                break

    events_7d = stats.events_7d if stats is not None else 0
    mass = stats.mass_total if stats is not None else 0

    if status in LINEAR_COMPLETED:
        return LIFECYCLE_COMPLETED
    if status in LINEAR_PLANNED and events_7d == 0:
        return LIFECYCLE_PLANNED
    if events_7d > 0:
        return LIFECYCLE_ACTIVE
    if status in LINEAR_ACTIVE:
        return LIFECYCLE_ACTIVE

    if events_30d is None:
        # Approximate dormant: no 7d activity but has mass
        if events_7d == 0 and mass > 0:
            return LIFECYCLE_DORMANT
    elif events_30d == 0 and mass > 0:
        return LIFECYCLE_DORMANT

    if status in LINEAR_PLANNED:
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
