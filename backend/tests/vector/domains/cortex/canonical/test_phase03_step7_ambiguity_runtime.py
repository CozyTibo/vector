"""Phase 03 Step 7 — ambiguity class/status vocabulary."""

from __future__ import annotations

from vector.domains.cortex.canonical.ambiguity_runtime import (
    AMBIGUITY_ENGINE_BUILD_REF,
    AMBIGUITY_RUNTIME_SCHEMA_VERSION,
    AmbiguityClass,
    AmbiguityStatus,
)


def test_ambiguity_runtime_constants() -> None:
    assert AMBIGUITY_RUNTIME_SCHEMA_VERSION >= 1
    assert AMBIGUITY_ENGINE_BUILD_REF


def test_ambiguity_classes_align_with_doctrine() -> None:
    values = {x.value for x in AmbiguityClass}
    assert "unresolved_mapping" in values
    assert "unresolved_identity" in values
    assert "conflicting_evidence" in values
    assert "competing_canonical_candidates" in values


def test_ambiguity_status_lifecycle_values() -> None:
    values = {x.value for x in AmbiguityStatus}
    assert "open" in values
    assert "superseded_by_evidence" in values
    assert "superseded_by_mapping_version" in values
    assert "void" in values
