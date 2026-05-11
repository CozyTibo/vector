"""Phase 03 Step 5 — static registry metadata merged into ontology JSON (no DB)."""

from __future__ import annotations

from typing import Any, Final

# Bump when registry surface fields or doctrine pointers change (not bundle rows).
MAPPING_REGISTRY_SURFACE_VERSION: Final[int] = 1

MAPPING_REGISTRY_DOCTRINE_ANCHORS: Final[tuple[str, ...]] = (
    "DOCS/cortex/03-canonical/phase-03-mapping-bundle-registry.md",
    "DOCS/cortex/03-canonical/phase-03-mapping-system-doctrine.md",
    "DOCS/cortex/03-canonical/phase-03-bundle-pinning-doctrine.md",
)


def build_mapping_registry_pointer_section() -> dict[str, Any]:
    """Embeddable slice for operator ontology document — points at DB-backed registry HTTP surface."""
    return {
        "mapping_registry_surface_version": MAPPING_REGISTRY_SURFACE_VERSION,
        "mapping_registry_admin_route": "GET /admin/tenants/{tenant_id}/cortex/canonical/mapping-registry",
        "mapping_registry_doctrine_anchors": list(MAPPING_REGISTRY_DOCTRINE_ANCHORS),
    }
