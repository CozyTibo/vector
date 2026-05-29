"""Declared domain stats sort and momentum rules."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.domains.cortex.declared_domains.stats import sort_domains
from vector.infrastructure.db.models.declared_domain import DeclaredDomain
from vector.infrastructure.db.models.declared_domain_stats import DeclaredDomainStats


def _domain(name: str) -> DeclaredDomain:
    now = datetime.now(UTC)
    return DeclaredDomain(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        display_name=name,
        declared_container_kind="project",
        seed_canon_entity_id=uuid.uuid4(),
        seed_connector="linear",
        seed_resource_type="linear.project",
        extractor_version=1,
        first_observed_at=now,
        created_at=now,
        updated_at=now,
    )


def _stats(*, mass: int, events_7d: int, prior: int, delta: int) -> DeclaredDomainStats:
    return DeclaredDomainStats(
        declared_domain_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        artifact_counts_json={},
        participant_count=0,
        events_7d=events_7d,
        events_prior_7d=prior,
        activity_delta_7d=delta,
        momentum_pct=None,
        mass_total=mass,
        expansion_level="direct",
        computed_at=datetime.now(UTC),
    )


def test_sort_growing_filters_low_baseline() -> None:
    d1 = _domain("A")
    d2 = _domain("B")
    s1 = _stats(mass=1, events_7d=10, prior=2, delta=8)
    s2 = _stats(mass=1, events_7d=20, prior=10, delta=10)
    s1.declared_domain_id = d1.id
    s2.declared_domain_id = d2.id
    ordered = sort_domains(
        [(d1, s1), (d2, s2)],
        sort="growing",
        activity_min_events=3,
        momentum_min_baseline=5,
    )
    assert [pair[0].display_name for pair in ordered] == ["B"]
