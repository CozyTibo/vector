"""Phase 1 step 1.5 — downstream chain proof evaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
)
from vector.domains.cortex.substrate_pipeline.continuity_p1_downstream import (
    evaluate_p1_5_downstream_proof_v1,
)


def _receipts_payload() -> dict:
    return {
        "phases": {
            PHASE_06_TCRE: {
                "status": "completed",
                "receipt_digest": "d06",
                "output_summary": {"async": True, "job_id": "j1"},
            },
            PHASE_07_RETRIEVAL: {
                "status": "completed",
                "receipt_digest": "d07",
                "output_summary": {"published_index_epoch": 1, "entries_materialized": 10},
            },
            PHASE_08_SYNTHESIS: {
                "status": "failed",
                "receipt_digest": "d08",
                "output_summary": {"jobs_completed": 0, "jobs_failed": 1},
            },
        },
        "tcre_jobs_completed": 2,
        "tcre_jobs_total": 3,
    }


def test_p1_5_pass_when_phases_and_tcre_complete() -> None:
    proof = evaluate_p1_5_downstream_proof_v1(
        closure_git_sha="abc" * 10,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        receipts=_receipts_payload(),
        tcre_footprint={"waiting_reason": "tcre_async"},
        deploy_recorded_at=datetime(2026, 5, 22, 23, 0, 0, tzinfo=UTC),
    )
    assert proof["p1_5_pass"] is True
    assert proof["verification"]["step_15_pass"] is True


def test_p1_5_fails_without_tcre_completed() -> None:
    receipts = _receipts_payload()
    receipts["tcre_jobs_completed"] = 0
    proof = evaluate_p1_5_downstream_proof_v1(
        closure_git_sha="abc" * 10,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        receipts=receipts,
        tcre_footprint={},
    )
    assert proof["p1_5_pass"] is False
