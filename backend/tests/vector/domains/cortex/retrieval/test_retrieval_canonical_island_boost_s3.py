"""Phase S3.3 — island canonical mat materialization boost."""

from __future__ import annotations

from vector.domains.cortex.retrieval.retrieval_canonical_materialization_v1 import (
    ISLAND_CANONICAL_BINDING_METADATA_KEYS_V1,
    get_retrieval_max_canonical_materializations_for_island_v1,
)


def test_island_binding_metadata_keys_include_source_anchor_ref() -> None:
    assert "canonical_entity_id" in ISLAND_CANONICAL_BINDING_METADATA_KEYS_V1
    assert "source_anchor_ref" in ISLAND_CANONICAL_BINDING_METADATA_KEYS_V1


def test_island_canonical_cap_scales_with_component_size() -> None:
    small = get_retrieval_max_canonical_materializations_for_island_v1(island_entity_count=10)
    large = get_retrieval_max_canonical_materializations_for_island_v1(island_entity_count=200)
    assert large >= small
    assert large == min(5000, max(small, 200 * 20))
