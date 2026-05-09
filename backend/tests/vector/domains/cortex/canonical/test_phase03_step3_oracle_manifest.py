"""Phase 03 Step 3 — oracle manifest shape + coverage tags."""

from __future__ import annotations

from vector.domains.cortex.canonical.oracle_manifest import (
    ORACLE_MANIFEST_SCHEMA_VERSION,
    build_oracle_manifest_public_document,
    oracle_vectors,
    validate_oracle_manifest_internal_consistency,
)


def test_oracle_manifest_schema_version() -> None:
    assert ORACLE_MANIFEST_SCHEMA_VERSION == 1


def test_validate_oracle_manifest() -> None:
    validate_oracle_manifest_internal_consistency()


def test_oracle_vectors_cover_mandatory_categories() -> None:
    tags: set[str] = set()
    for v in oracle_vectors():
        tags.update(v["coverage_tags"])
    assert "logical_key_stability" in tags or "per_canonical_class" in tags
    assert any("temporal" in t or "ordering" in t for t in tags)
    assert any("ambiguity" in t for t in tags)
    assert any("provenance" in t for t in tags)
    assert any("rebuild" in t for t in tags)
    assert any("C3" in t for t in tags)
    assert any("C4" in t for t in tags)
    assert any("C5" in t for t in tags)


def test_public_document_shape() -> None:
    doc = build_oracle_manifest_public_document()
    assert doc["vectors"]
    assert doc["mapping_bundle_id"]
