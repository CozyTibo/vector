"""Static metadata for Phase 03 Step 6 transform runtime (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

TRANSFORM_RUNTIME_SURFACE_VERSION: Final[int] = 4


def build_transform_runtime_pointer_section() -> dict[str, Any]:
    return {
        "transform_runtime_surface_version": TRANSFORM_RUNTIME_SURFACE_VERSION,
        "transform_materialize_route": (
            "POST /admin/tenants/{tenant_id}/cortex/canonical/transform/materialize"
        ),
        "transform_lineage_route": "GET /admin/tenants/{tenant_id}/cortex/canonical/transform/lineage",
        "transform_lineage_includes_confidence": True,
        "transform_supports_replay_job_link": True,
        "transform_emits_provenance_record": True,
        "transform_persists_temporal_ordering": True,
        "transform_runtime_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-transform-lineage-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-deterministic-canonicalization-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-replay-versioning-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-provenance-traceability-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-temporal-timeline-doctrine.md",
        ],
    }
