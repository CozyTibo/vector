"""Static metadata for Phase 04 Step 10 org link replay (merged into ontology JSON)."""

from __future__ import annotations

from typing import Any, Final

ORG_LINK_REPLAY_RUNTIME_SURFACE_VERSION: Final[int] = 2


def build_org_link_replay_pointer_section() -> dict[str, Any]:
    return {
        "org_link_replay_runtime_surface_version": ORG_LINK_REPLAY_RUNTIME_SURFACE_VERSION,
        "org_link_replay_jobs_list_route": "GET /admin/tenants/{tenant_id}/cortex/identity/replay-jobs",
        "org_link_replay_job_detail_route": "GET /admin/tenants/{tenant_id}/cortex/identity/replay-jobs/{job_id}",
        "org_link_replay_job_run_route": "POST /admin/tenants/{tenant_id}/cortex/identity/replay-jobs/run",
        "org_link_replay_job_enqueue_route": "POST /admin/tenants/{tenant_id}/cortex/identity/replay-jobs/enqueue",
        "identity_worker_task_status_route": (
            "GET /admin/tenants/{tenant_id}/cortex/identity/worker-tasks/{celery_task_id}"
        ),
        "org_link_replay_drift_taxonomy": [
            {"class": f"L{i}", "meaning": "Reserved link-layer drift / parity class (P04-10); L0 = snapshot recorded."}
            for i in range(8)
        ],
        "celery_task_run_org_link_replay_job": "vector.cortex.identity.run_org_link_replay_job",
        "org_link_replay_runtime_doctrine_anchors": [
            "DOCS/cortex/04-identity/phase-04-continuity-replay-doctrine.md",
        ],
    }
