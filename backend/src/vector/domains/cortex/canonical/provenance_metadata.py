"""Static metadata for Phase 03 Step 11 provenance runtime (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

PROVENANCE_RUNTIME_SURFACE_VERSION: Final[int] = 1


def build_provenance_runtime_pointer_section() -> dict[str, Any]:
    return {
        "provenance_runtime_surface_version": PROVENANCE_RUNTIME_SURFACE_VERSION,
        "provenance_by_raw_record_route": (
            "GET /admin/tenants/{tenant_id}/cortex/canonical/provenance/raw-records/{raw_record_id}"
        ),
        "provenance_by_materialization_route": (
            "GET /admin/tenants/{tenant_id}/cortex/canonical/provenance/materializations/{materialization_id}"
        ),
        "provenance_evidence_shapes_documented": ["1:1", "N:1", "1:N", "many:many"],
        "provenance_runtime_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-provenance-traceability-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-transform-lineage-doctrine.md",
        ],
    }
