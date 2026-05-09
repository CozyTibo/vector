"""Static metadata for Phase 03 Step 9 identity continuity (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

IDENTITY_RUNTIME_SURFACE_VERSION: Final[int] = 1


def build_identity_runtime_pointer_section() -> dict[str, Any]:
    return {
        "identity_runtime_surface_version": IDENTITY_RUNTIME_SURFACE_VERSION,
        "identity_anchors_list_route": "GET /admin/tenants/{tenant_id}/cortex/canonical/identity/anchors",
        "identity_anchor_detail_route": (
            "GET /admin/tenants/{tenant_id}/cortex/canonical/identity/anchors/{canonical_entity_id}"
        ),
        "identity_runtime_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-identity-continuity-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-ambiguity-confidence-doctrine.md",
        ],
    }
