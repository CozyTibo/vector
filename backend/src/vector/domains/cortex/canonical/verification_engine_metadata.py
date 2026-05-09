"""Static metadata for Phase 03 Step 15 verification engine (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

VERIFICATION_ENGINE_SURFACE_VERSION: Final[int] = 1


def build_verification_engine_pointer_section() -> dict[str, Any]:
    return {
        "verification_engine_surface_version": VERIFICATION_ENGINE_SURFACE_VERSION,
        "canonical_verification_run_route": (
            "POST /admin/tenants/{tenant_id}/cortex/canonical/verification/run"
        ),
        "canonical_verification_runs_list_route": (
            "GET /admin/tenants/{tenant_id}/cortex/canonical/verification/runs"
        ),
        "verification_engine_gate_ids": [
            "G-P03-01",
            "G-P03-02",
            "G-P03-03",
            "G-P03-04",
            "G-P03-06",
            "G-P03-08",
            "G-P03-09",
            "G-P03-10",
            "G-P03-16",
            "G-P03-17",
            "G-P03-21",
            "G-P03-22",
            "G-P03-23",
            "G-P03-24",
        ],
        "verification_engine_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-verification-engine-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-closure-gates-doctrine.md",
        ],
    }
