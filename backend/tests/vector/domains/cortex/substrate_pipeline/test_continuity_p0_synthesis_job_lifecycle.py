"""Phase A step A1 — continuity proof evaluation."""

from __future__ import annotations

import uuid

from vector.domains.cortex.substrate_pipeline.continuity_p0_synthesis_job_lifecycle import (
    evaluate_p0_a1_synthesis_job_lifecycle_proof_v1,
    verify_a1_synthesis_job_lifecycle_wiring_v1,
)


def test_a1_wiring_static() -> None:
    wiring = verify_a1_synthesis_job_lifecycle_wiring_v1()
    assert wiring["wiring_ok"] is True


def test_a1_pass_after_reconcile() -> None:
    tenant = str(uuid.uuid4())
    snapshot = {
        "tenant_id": tenant,
        "histogram": {"running": 0, "failed": 1043, "completed": 1},
        "running_count": 0,
        "stale_running_count": 0,
        "running_alert_threshold": 10,
        "stale_after_seconds": 86_400,
        "wiring": {"wiring_ok": True},
    }
    reconcile = {
        "histogram_before": {"running": 1043},
        "histogram_after": {"running": 0, "failed": 1043},
        "reconciled_count": 1043,
        "stale_running_after": 0,
    }
    proof = evaluate_p0_a1_synthesis_job_lifecycle_proof_v1(
        closure_git_sha="abc123",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        reconcile_drive=reconcile,
        trace_only=False,
    )
    assert proof["p0_a1_pass"] is True
    assert proof["checks"]["running_below_threshold"] is True
