"""Static metadata for Phase 04 Step 9 bundle equivalence admin surface (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

BUNDLE_EQUIVALENCE_RUNTIME_SURFACE_VERSION: Final[int] = 1


def build_bundle_equivalence_pointer_section() -> dict[str, Any]:
    return {
        "bundle_equivalence_runtime_surface_version": BUNDLE_EQUIVALENCE_RUNTIME_SURFACE_VERSION,
        "bundle_equivalence_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/bundle-equivalence",
        "bundle_equivalence_append_route": "POST /admin/tenants/{tenant_id}/cortex/identity/bundle-equivalence",
        "bundle_equivalence_runtime_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-cross-bundle-equivalence-doctrine.md",
        ],
    }
