"""Static metadata for Phase 04 merge governance admin surface (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

MERGE_GOVERNANCE_RUNTIME_SURFACE_VERSION: Final[int] = 2


def build_merge_governance_pointer_section() -> dict[str, Any]:
    return {
        "merge_governance_runtime_surface_version": MERGE_GOVERNANCE_RUNTIME_SURFACE_VERSION,
        "merge_ledger_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/merges",
        "merge_ledger_append_route": "POST /admin/tenants/{tenant_id}/cortex/identity/merges",
        "merge_queue_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/merge-queue",
        "merge_queue_detail_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/merge-queue/{merge_proposal_id}"
        ),
        "merge_governance_runtime_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-merge-governance-doctrine.md",
        ],
    }
