"""Phase 03 Step 2 — canonical object taxonomy invariants."""

from __future__ import annotations

from vector.domains.cortex.canonical.ontology import CanonicalLayerKind, CanonicalObjectKind, layer_for_kind
from vector.domains.cortex.canonical.taxonomy import (
    CanonicalStructuralRole,
    build_taxonomy_public_section,
    structural_role_for_kind,
    validate_taxonomy_internal_consistency,
)


def test_validate_taxonomy_internal_consistency_passes() -> None:
    validate_taxonomy_internal_consistency()


def test_relationship_reference_snapshot_roles_match_layers() -> None:
    assert structural_role_for_kind(CanonicalObjectKind.RELATIONSHIP_EDGE) == CanonicalStructuralRole.LINKAGE
    assert structural_role_for_kind(CanonicalObjectKind.CANONICAL_REFERENCE) == CanonicalStructuralRole.POINTER
    assert structural_role_for_kind(CanonicalObjectKind.STATE_SNAPSHOT) == CanonicalStructuralRole.PROJECTION
    assert layer_for_kind(CanonicalObjectKind.RELATIONSHIP_EDGE) == CanonicalLayerKind.RELATIONSHIP


def test_taxonomy_public_section_keys_and_alignment() -> None:
    sec = build_taxonomy_public_section()
    assert set(sec.keys()) == {"taxonomy_families", "kind_taxonomy", "taxonomy_hard_rules"}
    assert len(sec["taxonomy_families"]) == len(CanonicalLayerKind)
    kind_ids = {x["object_kind_id"] for x in sec["kind_taxonomy"]}
    assert kind_ids == {k.value for k in CanonicalObjectKind}
