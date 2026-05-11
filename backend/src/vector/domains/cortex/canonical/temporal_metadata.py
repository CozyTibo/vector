"""Static metadata for Phase 03 Step 12 temporal runtime (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

TEMPORAL_RUNTIME_SURFACE_VERSION: Final[int] = 1


def build_temporal_runtime_pointer_section() -> dict[str, Any]:
    return {
        "temporal_runtime_surface_version": TEMPORAL_RUNTIME_SURFACE_VERSION,
        "temporal_supersessions_list_route": (
            "GET /admin/tenants/{tenant_id}/cortex/canonical/temporal/supersessions"
        ),
        "temporal_rebuild_preview_route": (
            "POST /admin/tenants/{tenant_id}/cortex/canonical/temporal/rebuild-preview"
        ),
        "temporal_ordering_precedence": [
            "occurred_at (UTC-normalized provider evidence when present)",
            "replay_sequence (Phase 01 ingest monotonic cursor)",
            "source_revision_key",
            "raw_record_id decimal tie-break",
        ],
        "temporal_runtime_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-temporal-timeline-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-replay-versioning-doctrine.md",
        ],
    }
