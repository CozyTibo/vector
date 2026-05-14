"""Static metadata for Phase 04 Step 15 org identity verification slice (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION: Final[int] = 2


def build_org_identity_verification_pointer_section() -> dict[str, Any]:
    return {
        "org_identity_verification_engine_schema_version": ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION,
        "org_identity_verification_run_route": (
            "POST /admin/tenants/{tenant_id}/cortex/identity/verification/run"
        ),
        "org_identity_verification_runs_list_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/verification/runs"
        ),
        "org_identity_verification_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-verification-gates-doctrine.md",
            "DOCS/cortex/05-traversal/phase-05-tenant-verification-integration.md",
        ],
    }
