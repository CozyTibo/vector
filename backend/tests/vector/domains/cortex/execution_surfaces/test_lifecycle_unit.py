"""Lifecycle bucket rules for declared domains."""

from vector.domains.cortex.execution_surfaces.lifecycle import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_COMPLETED,
    LIFECYCLE_DORMANT,
    LIFECYCLE_PLANNED,
    lifecycle_bucket_for_domain,
    matches_lifecycle_filter,
)
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain_stats import DeclaredDomainStats


def _stats(events_7d: int = 0, events_prior: int = 0, mass: int = 0) -> DeclaredDomainStats:
    row = DeclaredDomainStats(
        declared_domain_id=None,  # type: ignore[arg-type]
        tenant_id=None,  # type: ignore[arg-type]
        artifact_counts_json={},
        participant_count=0,
        events_7d=events_7d,
        events_prior_7d=events_prior,
        activity_delta_7d=events_7d - events_prior,
        mass_total=mass,
        expansion_level="direct",
        computed_at=None,  # type: ignore[arg-type]
    )
    return row


def test_lifecycle_completed_from_provider_status() -> None:
    seed = CanonEntity(
        tenant_id=None,  # type: ignore[arg-type]
        connection_id=None,  # type: ignore[arg-type]
        entity_type="project",
        entity_key="k",
        display_label="x",
        connector="linear",
        attrs_json={"state": "completed"},
    )
    assert lifecycle_bucket_for_domain(seed_entity=seed, stats=_stats()) == LIFECYCLE_COMPLETED


def test_lifecycle_active_from_observation_events() -> None:
    assert (
        lifecycle_bucket_for_domain(seed_entity=None, stats=_stats(events_7d=2))
        == LIFECYCLE_ACTIVE
    )


def test_lifecycle_dormant_when_no_recent_observation() -> None:
    assert (
        lifecycle_bucket_for_domain(
            seed_entity=None,
            stats=_stats(events_7d=0, mass=10),
            events_30d=0,
        )
        == LIFECYCLE_DORMANT
    )


def test_lifecycle_planned_status_no_events() -> None:
    seed = CanonEntity(
        tenant_id=None,  # type: ignore[arg-type]
        connection_id=None,  # type: ignore[arg-type]
        entity_type="project",
        entity_key="k",
        display_label="x",
        connector="linear",
        attrs_json={"status": "backlog"},
    )
    assert lifecycle_bucket_for_domain(seed_entity=seed, stats=_stats()) == LIFECYCLE_PLANNED


def test_matches_lifecycle_filter() -> None:
    assert matches_lifecycle_filter(LIFECYCLE_ACTIVE, "active")
    assert matches_lifecycle_filter(LIFECYCLE_ACTIVE, None)
    assert not matches_lifecycle_filter(LIFECYCLE_PLANNED, "active")
