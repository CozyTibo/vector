"""Phase 03 Step 5 — mapping registry pointer metadata (no DB)."""

from __future__ import annotations

from vector.domains.cortex.canonical.mapping_registry_metadata import (
    MAPPING_REGISTRY_SURFACE_VERSION,
    build_mapping_registry_pointer_section,
)


def test_mapping_registry_surface_version() -> None:
    assert MAPPING_REGISTRY_SURFACE_VERSION == 1


def test_pointer_section_keys() -> None:
    sec = build_mapping_registry_pointer_section()
    assert sec["mapping_registry_surface_version"] == MAPPING_REGISTRY_SURFACE_VERSION
    assert "tenant_id" not in sec
    assert "mapping-registry" in sec["mapping_registry_admin_route"]
