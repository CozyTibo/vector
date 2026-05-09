"""Static metadata for Phase 03 Step 7 ambiguity persistence (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

AMBIGUITY_RUNTIME_SURFACE_VERSION: Final[int] = 1


def build_ambiguity_runtime_pointer_section() -> dict[str, Any]:
    return {
        "ambiguity_runtime_surface_version": AMBIGUITY_RUNTIME_SURFACE_VERSION,
        "ambiguity_list_route": "GET /admin/tenants/{tenant_id}/cortex/canonical/ambiguity",
        "ambiguity_open_route": "POST /admin/tenants/{tenant_id}/cortex/canonical/ambiguity",
        "ambiguity_detail_route": "GET /admin/tenants/{tenant_id}/cortex/canonical/ambiguity/{ambiguity_id}",
        "ambiguity_lifecycle_route": (
            "POST /admin/tenants/{tenant_id}/cortex/canonical/ambiguity/{ambiguity_id}/lifecycle"
        ),
        "ambiguity_runtime_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-ambiguity-confidence-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-deterministic-canonicalization-doctrine.md",
        ],
    }
