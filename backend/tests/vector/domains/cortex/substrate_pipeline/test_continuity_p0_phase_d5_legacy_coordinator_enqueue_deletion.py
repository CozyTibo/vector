"""Phase D5 — legacy coordinator enqueue paths deleted."""

from __future__ import annotations

from vector.domains.cortex.execution.scheduling import (
    verify_d5_legacy_coordinator_enqueue_paths_deleted_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_d5_legacy_coordinator_enqueue_deletion import (
    PHASE_D5_COORDINATOR_DELETION_SCHEMA_VERSION,
    evaluate_p0_d5_legacy_coordinator_deletion_proof_v1,
    verify_d5_legacy_coordinator_deletion_wiring_v1,
)


def test_d5_wiring_ok() -> None:
    assert verify_d5_legacy_coordinator_enqueue_paths_deleted_v1() == []
    wiring = verify_d5_legacy_coordinator_deletion_wiring_v1()
    assert wiring["wiring_ok"] is True
    assert wiring["m4_schedule_gate_ok"] is True


def test_d5_proof_passes() -> None:
    snapshot = {
        "doc_enabled": True,
        "authoritative_motion_path": "mark_dirty_and_enqueue_convergence_v1",
        "celery_execution_task": "vector.cortex.execution.run_slice",
        "wiring": {
            "wiring_ok": True,
            "m4_schedule_gate_ok": True,
            "coordinator_enqueue_deleted_flag_default": True,
            "phase_d5_schema_version": PHASE_D5_COORDINATOR_DELETION_SCHEMA_VERSION,
            "errors": [],
        },
    }
    proof = evaluate_p0_d5_legacy_coordinator_deletion_proof_v1(
        closure_git_sha="abc",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
    )
    assert proof["p0_d5_pass"] is True
    assert proof["verification"]["phase_d_parallel_complete"] is True
