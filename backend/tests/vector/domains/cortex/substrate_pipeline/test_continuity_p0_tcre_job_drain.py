"""Phase A step A3 — TCRE drain proof evaluator."""

from __future__ import annotations

import uuid

from vector.domains.cortex.substrate_pipeline.continuity_p0_tcre_job_drain import (
    evaluate_p0_a3_tcre_job_drain_proof_v1,
    verify_a3_tcre_job_drain_wiring_v1,
)


def test_a3_wiring_static() -> None:
    wiring = verify_a3_tcre_job_drain_wiring_v1()
    assert wiring["wiring_ok"] is True


def test_a3_pass_after_drain() -> None:
    tenant = str(uuid.uuid4())
    snapshot = {
        "tenant_id": tenant,
        "histogram": {"queued": 0, "completed": 3},
        "stale_queued_count": 0,
        "queued_stale_seconds": 3600,
        "wiring": {"wiring_ok": True},
    }
    drain = {
        "stale_queued_before": 1,
        "stale_queued_after": 0,
        "jobs_drained": 1,
        "histogram_after": {"queued": 0, "completed": 3},
        "drained_jobs": [
            {
                "job_id": str(uuid.uuid4()),
                "status": "completed",
                "resume": {
                    "resumed": True,
                    "path": "convergence_lease",
                    "lease": {"phase_cursor": "phase_07_retrieval"},
                },
            },
        ],
    }
    proof = evaluate_p0_a3_tcre_job_drain_proof_v1(
        closure_git_sha="abc",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        drain_drive=drain,
    )
    assert proof["p0_a3_pass"] is True
