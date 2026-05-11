"""Static metadata for Phase 04 Step 20 anchor → org handle backfill (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.identity.backfill import ORG_IDENTITY_BACKFILL_SCHEMA_VERSION

ORG_IDENTITY_BACKFILL_SURFACE_VERSION: Final[int] = 1


def build_org_identity_backfill_pointer_section() -> dict[str, Any]:
    return {
        "org_identity_backfill_surface_version": ORG_IDENTITY_BACKFILL_SURFACE_VERSION,
        "org_identity_backfill_schema_version": ORG_IDENTITY_BACKFILL_SCHEMA_VERSION,
        "org_identity_backfill_from_anchors_route": (
            "POST /admin/tenants/{tenant_id}/cortex/identity/backfill/from-canonical-anchors"
        ),
        "org_identity_backfill_runs_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/backfill/runs"
        ),
        "org_identity_backfill_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-backfill-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-mock-data-strategy.md",
        ],
    }
