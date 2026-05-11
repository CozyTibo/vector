"""Static metadata for Phase 04 Step 22 org identity certification pack (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

ORG_IDENTITY_CERTIFICATION_PACK_SURFACE_VERSION: Final[int] = 1


def build_org_identity_certification_pack_pointer_section() -> dict[str, Any]:
    return {
        "org_identity_certification_pack_surface_version": ORG_IDENTITY_CERTIFICATION_PACK_SURFACE_VERSION,
        "org_identity_certification_pack_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/certification-pack"
        ),
        "org_identity_certification_pack_archive_route": (
            "POST /admin/tenants/{tenant_id}/cortex/identity/certification-pack/archive"
        ),
        "org_identity_certification_pack_archives_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/certification-pack/archives"
        ),
        "org_identity_certification_pack_archive_detail_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/certification-pack/archives/{archive_id}"
        ),
        "org_identity_certification_pack_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-closure-gates-doctrine.md",
        ],
    }
