"""Static metadata for Phase 04 Step 13 OrgGraphProjectionV1 export (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

ORG_GRAPH_PROJECTION_EXPORT_SURFACE_VERSION: Final[int] = 3


def build_org_graph_projection_export_pointer_section() -> dict[str, Any]:
    return {
        "org_graph_projection_export_surface_version": ORG_GRAPH_PROJECTION_EXPORT_SURFACE_VERSION,
        "org_graph_projection_export_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/graph-projection"
        ),
        "org_graph_projection_preview_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/projection-preview"
        ),
        "org_graph_projection_export_async_run_route": (
            "POST /admin/tenants/{tenant_id}/cortex/identity/projection-export/run"
        ),
        "org_graph_projection_export_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-graph-boundary-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-graph-projection-export-doctrine.md",
        ],
    }
