"""Static metadata for Phase 03 Step 13 canonical query runtime (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

CANONICAL_QUERY_SURFACE_VERSION: Final[int] = 1


def build_canonical_query_pointer_section() -> dict[str, Any]:
    return {
        "canonical_query_surface_version": CANONICAL_QUERY_SURFACE_VERSION,
        "canonical_query_route": "POST /admin/tenants/{tenant_id}/cortex/canonical/query",
        "canonical_query_classes": [
            "point_lookup_materialization",
            "point_lookup_identity_anchor",
            "evidence_backtrace",
            "forward_trace",
            "timeline_slice",
            "graph_neighborhood",
            "replay_debug_snapshot",
        ],
        "canonical_query_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-canonical-query-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-anti-goals-doctrine.md",
        ],
    }
