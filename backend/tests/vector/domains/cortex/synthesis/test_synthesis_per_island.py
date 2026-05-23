"""P2-D per-island synthesis unit tests."""

from __future__ import annotations

from vector.domains.cortex.synthesis.synthesis_per_island import (
    GLOBAL_DEGRADATION_BRIEF_SURFACE_V1,
    SYNTHESIS_OMISSION_OUTSIDE_ISLAND_SCOPE_V1,
    build_global_degradation_brief_v1,
)


def test_global_degradation_brief_outside_island_scope() -> None:
    islands = [
        {"island_scope_id": "scope-a", "entity_count": 100, "authoritative_edge_count": 50},
        {"island_scope_id": "scope-b", "entity_count": 2, "authoritative_edge_count": 1},
    ]
    results = [
        {
            "island_scope_id": "scope-a",
            "retrieval_entries_in_scope": 3,
            "jobs_completed": 1,
            "jobs_failed": 0,
            "artifact_digests": ["digest-a"],
        },
        {
            "island_scope_id": "scope-b",
            "retrieval_entries_in_scope": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "artifact_digests": [],
        },
    ]
    brief = build_global_degradation_brief_v1(
        tenant_entity_count=500,
        islands=islands,
        island_results=results,
        published_index_epoch="epoch-1",
    )
    assert brief["surface_kind"] == GLOBAL_DEGRADATION_BRIEF_SURFACE_V1
    assert brief["outside_island_scope_entity_count"] == 398
    assert brief["islands_synthesized_count"] == 1
    assert brief["islands"][0]["synthesis_omission"] == SYNTHESIS_OMISSION_OUTSIDE_ISLAND_SCOPE_V1
