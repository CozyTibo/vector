"""Static metadata for Phase 04 Step 12 execution primitive persistence (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

EXECUTION_PRIMITIVE_PERSISTENCE_SURFACE_VERSION: Final[int] = 2


def build_execution_primitive_persistence_pointer_section() -> dict[str, Any]:
    return {
        "execution_primitive_persistence_surface_version": EXECUTION_PRIMITIVE_PERSISTENCE_SURFACE_VERSION,
        "org_primitive_instances_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/primitive-instances",
        "org_primitive_explorer_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/primitives",
        "org_primitive_explorer_detail_route": "GET /admin/tenants/{tenant_id}/cortex/identity/primitives/{primitive_id}",
        "org_primitive_instance_detail_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/primitive-instances/{instance_id}"
        ),
        "org_primitive_instance_append_route": "POST /admin/tenants/{tenant_id}/cortex/identity/primitive-instances",
        "execution_primitive_persistence_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-execution-primitive-persistence-doctrine.md",
        ],
    }
