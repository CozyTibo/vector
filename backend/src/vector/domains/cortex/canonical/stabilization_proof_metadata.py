"""Static metadata for Phase 03 Step 17 stabilization proof (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

STABILIZATION_PROOF_SURFACE_VERSION: Final[int] = 1


def build_stabilization_proof_pointer_section() -> dict[str, Any]:
    return {
        "stabilization_proof_surface_version": STABILIZATION_PROOF_SURFACE_VERSION,
        "canonical_stabilization_proof_route": (
            "GET /admin/tenants/{tenant_id}/cortex/canonical/stabilization-proof"
        ),
        "canonical_stabilization_proof_run_route": (
            "POST /admin/tenants/{tenant_id}/cortex/canonical/stabilization-proof/run"
        ),
        "canonical_stabilization_proof_runs_route": (
            "GET /admin/tenants/{tenant_id}/cortex/canonical/stabilization-proof/runs"
        ),
        "stabilization_proof_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-implementation-readiness-audit.md",
        ],
    }
