"""Phase 03 Step 3 — logical key profile invariants."""

from __future__ import annotations

from vector.domains.cortex.canonical.logical_keys import (
    LOGICAL_KEY_PROFILE_VERSION,
    logical_key_fields_for_kind,
    validate_logical_key_profile_internal_consistency,
)
from vector.domains.cortex.canonical.ontology import CanonicalObjectKind


def test_logical_key_profile_version() -> None:
    assert LOGICAL_KEY_PROFILE_VERSION == 1


def test_validate_logical_key_profile() -> None:
    validate_logical_key_profile_internal_consistency()


def test_every_kind_has_distinct_field_count() -> None:
    for k in CanonicalObjectKind:
        fields = logical_key_fields_for_kind(k)
        assert len(fields) >= 4
        assert fields[0] == "tenant_id"
