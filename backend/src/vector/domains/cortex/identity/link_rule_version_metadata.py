"""Static metadata for Phase 04 Step 11 linkage rule versions (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

LINK_RULE_VERSION_RUNTIME_SURFACE_VERSION: Final[int] = 1


def build_link_rule_version_pointer_section() -> dict[str, Any]:
    return {
        "link_rule_version_runtime_surface_version": LINK_RULE_VERSION_RUNTIME_SURFACE_VERSION,
        "link_rule_versions_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/link-rule-versions",
        "link_rule_version_detail_route": "GET /admin/tenants/{tenant_id}/cortex/identity/link-rule-versions/{rule_version_id}",
        "link_rule_version_append_route": "POST /admin/tenants/{tenant_id}/cortex/identity/link-rule-versions",
        "link_rule_version_runtime_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-linkage-rule-engine-doctrine.md",
        ],
    }
