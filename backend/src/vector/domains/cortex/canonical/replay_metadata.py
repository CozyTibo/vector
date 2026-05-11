"""Static metadata for Phase 03 Step 10 replay / rebuild runtime (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

REPLAY_RUNTIME_SURFACE_VERSION: Final[int] = 1


def build_replay_runtime_pointer_section() -> dict[str, Any]:
    return {
        "replay_runtime_surface_version": REPLAY_RUNTIME_SURFACE_VERSION,
        "replay_jobs_list_route": "GET /admin/tenants/{tenant_id}/cortex/canonical/replay-jobs",
        "replay_job_detail_route": "GET /admin/tenants/{tenant_id}/cortex/canonical/replay-jobs/{job_id}",
        "replay_job_run_route": "POST /admin/tenants/{tenant_id}/cortex/canonical/replay-jobs/run",
        "replay_divergence_taxonomy": [
            {"class": "C0", "meaning": "Bitwise-identical canonical projection vs oracle (or first materialization)."},
            {"class": "C1", "meaning": "Reserved — equivalent under declared normalization (not auto-detected in v1)."},
            {"class": "C2", "meaning": "Expected drift under regeneration / declared mapping migration (PASS with receipt)."},
            {"class": "C3", "meaning": "Raw substrate / trust mismatch vs Phase 02 expectations (FAIL; no write)."},
            {"class": "C4", "meaning": "Unexpected drift or oracle resolution failure under rebuild (FAIL; no write)."},
            {"class": "C5", "meaning": "Bundle migration without declared compatibility edge (FAIL; job rejected)."},
        ],
        "replay_runtime_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-replay-versioning-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-bundle-pinning-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-transform-lineage-doctrine.md",
        ],
    }
