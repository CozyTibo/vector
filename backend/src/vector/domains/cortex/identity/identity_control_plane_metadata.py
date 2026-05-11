"""Static metadata for Phase 04 Step 17 identity control plane (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

IDENTITY_CONTROL_PLANE_SURFACE_VERSION: Final[int] = 6


def build_identity_control_plane_pointer_section() -> dict[str, Any]:
    return {
        "identity_control_plane_surface_version": IDENTITY_CONTROL_PLANE_SURFACE_VERSION,
        "identity_control_plane_route": "GET /admin/tenants/{tenant_id}/cortex/identity/control-plane",
        "identity_control_plane_contract": "identity_control_plane_v1",
        "identity_operator_console_surface_version": 1,
        "identity_operator_console_http_routes": [
            "GET /admin/tenants/{tenant_id}/cortex/identity/handles",
            "GET /admin/tenants/{tenant_id}/cortex/identity/handles/{handle_id}",
            "GET /admin/tenants/{tenant_id}/cortex/identity/links",
            "GET /admin/tenants/{tenant_id}/cortex/identity/links/{link_id}",
            "POST /admin/tenants/{tenant_id}/cortex/identity/links/{link_id}/revoke",
            "GET /admin/tenants/{tenant_id}/cortex/identity/merge-queue",
            "GET /admin/tenants/{tenant_id}/cortex/identity/merge-queue/{merge_proposal_id}",
            "POST /admin/tenants/{tenant_id}/cortex/identity/merge-queue/{merge_proposal_id}/approve",
            "POST /admin/tenants/{tenant_id}/cortex/identity/merge-queue/{merge_proposal_id}/reject",
            "POST /admin/tenants/{tenant_id}/cortex/identity/merge-queue/{merge_proposal_id}/defer",
            "POST /admin/tenants/{tenant_id}/cortex/identity/merge-queue/{merge_proposal_id}/split",
            "GET /admin/tenants/{tenant_id}/cortex/identity/ambiguity-queue",
            "GET /admin/tenants/{tenant_id}/cortex/identity/ambiguity-queue/{ambiguity_id}",
            "GET /admin/tenants/{tenant_id}/cortex/identity/primitives",
            "GET /admin/tenants/{tenant_id}/cortex/identity/primitives/{primitive_id}",
            "GET /admin/tenants/{tenant_id}/cortex/identity/projection-preview",
            "POST /admin/tenants/{tenant_id}/cortex/identity/projection-export/run",
            "POST /admin/tenants/{tenant_id}/cortex/identity/replay-jobs/enqueue",
            "GET /admin/tenants/{tenant_id}/cortex/identity/worker-tasks/{celery_task_id}",
            "POST /admin/tenants/{tenant_id}/cortex/identity/link-candidates/regenerate-async",
            "POST /admin/tenants/{tenant_id}/cortex/identity/authoritative-replay-async",
            "POST /admin/tenants/{tenant_id}/cortex/identity/backfill/from-canonical-anchors",
            "GET /admin/tenants/{tenant_id}/cortex/identity/backfill/runs",
            "GET /admin/tenants/{tenant_id}/cortex/identity/readiness-economics",
            "GET /admin/tenants/{tenant_id}/cortex/identity/certification-pack",
            "POST /admin/tenants/{tenant_id}/cortex/identity/certification-pack/archive",
            "GET /admin/tenants/{tenant_id}/cortex/identity/certification-pack/archives",
            "GET /admin/tenants/{tenant_id}/cortex/identity/certification-pack/archives/{archive_id}",
        ],
        "identity_control_plane_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-control-plane-doctrine.md",
        ],
    }
