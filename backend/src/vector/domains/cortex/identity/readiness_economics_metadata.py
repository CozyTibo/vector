"""Static metadata for Phase 04 Step 21 identity readiness economics (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.identity.readiness_economics import (
    IDENTITY_READINESS_ECONOMICS_CONTRACT,
    IDENTITY_READINESS_ECONOMICS_SCHEMA_VERSION,
)

IDENTITY_READINESS_ECONOMICS_SURFACE_VERSION: Final[int] = 1


def build_identity_readiness_economics_pointer_section() -> dict[str, Any]:
    return {
        "identity_readiness_economics_surface_version": IDENTITY_READINESS_ECONOMICS_SURFACE_VERSION,
        "identity_readiness_economics_schema_version": IDENTITY_READINESS_ECONOMICS_SCHEMA_VERSION,
        "identity_readiness_economics_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/readiness-economics"
        ),
        "identity_readiness_economics_contract": IDENTITY_READINESS_ECONOMICS_CONTRACT,
        "identity_readiness_economics_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-readiness-audit.md",
        ],
    }
