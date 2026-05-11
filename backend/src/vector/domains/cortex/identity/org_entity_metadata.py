"""Static metadata for Phase 04 org entity admin surface (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

ORG_ENTITY_RUNTIME_SURFACE_VERSION: Final[int] = 2


def build_org_entity_pointer_section() -> dict[str, Any]:
    return {
        "org_entity_runtime_surface_version": ORG_ENTITY_RUNTIME_SURFACE_VERSION,
        "org_entity_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/entities",
        "org_entity_detail_route": "GET /admin/tenants/{tenant_id}/cortex/identity/entities/{org_entity_id}",
        "org_handle_explorer_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/handles",
        "org_handle_explorer_detail_route": "GET /admin/tenants/{tenant_id}/cortex/identity/handles/{handle_id}",
        "org_entity_runtime_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-org-entity-and-handle-doctrine.md",
        ],
    }
