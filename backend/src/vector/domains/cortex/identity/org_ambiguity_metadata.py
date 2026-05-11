"""Static metadata for Phase 04 Step 14 org ambiguity runtime (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

ORG_AMBIGUITY_RUNTIME_SURFACE_VERSION: Final[int] = 2


def build_org_ambiguity_runtime_pointer_section() -> dict[str, Any]:
    return {
        "org_ambiguity_runtime_surface_version": ORG_AMBIGUITY_RUNTIME_SURFACE_VERSION,
        "org_ambiguities_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/org-ambiguities",
        "org_ambiguity_detail_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/org-ambiguities/{record_id}"
        ),
        "org_ambiguity_queue_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/ambiguity-queue",
        "org_ambiguity_queue_detail_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/ambiguity-queue/{ambiguity_id}"
        ),
        "org_ambiguity_append_route": "POST /admin/tenants/{tenant_id}/cortex/identity/org-ambiguities",
        "org_ambiguity_runtime_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-ambiguity-multiple-persona-doctrine.md",
        ],
    }
