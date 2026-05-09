"""Static metadata for Phase 03 Step 16 canonical control plane (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

CONTROL_PLANE_SURFACE_VERSION: Final[int] = 1


def build_control_plane_pointer_section() -> dict[str, Any]:
    return {
        "canonical_control_plane_surface_version": CONTROL_PLANE_SURFACE_VERSION,
        "canonical_control_plane_route": (
            "GET /admin/tenants/{tenant_id}/cortex/canonical/control-plane"
        ),
        "canonical_control_plane_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-canonical-control-plane-doctrine.md",
        ],
    }
