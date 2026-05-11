"""Static metadata for Phase 03 Step 18 certification pack (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

CERTIFICATION_PACK_SURFACE_VERSION: Final[int] = 1


def build_certification_pack_pointer_section() -> dict[str, Any]:
    return {
        "certification_pack_surface_version": CERTIFICATION_PACK_SURFACE_VERSION,
        "canonical_certification_pack_route": (
            "GET /admin/tenants/{tenant_id}/cortex/canonical/certification-pack"
        ),
        "canonical_certification_pack_archive_route": (
            "POST /admin/tenants/{tenant_id}/cortex/canonical/certification-pack/archive"
        ),
        "canonical_certification_pack_archives_route": (
            "GET /admin/tenants/{tenant_id}/cortex/canonical/certification-pack/archives"
        ),
        "certification_pack_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-closure-gates-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-canonical-control-plane-doctrine.md",
        ],
    }
