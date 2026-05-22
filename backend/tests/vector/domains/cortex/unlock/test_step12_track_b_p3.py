"""Step 12 Fix 6–7, soak, and L6 synthesis legality."""

from __future__ import annotations

from vector.domains.cortex.unlock.step12_track_b_p3 import (
    TRACK_B_SOAK_HOURS_REQUIRED_V1,
    evaluate_fix6_github_ingest_caps_v1,
    evaluate_fix7_admin_metric_truth_v1,
    evaluate_l6_synthesis_legality_v1,
    evaluate_p2_autonomous_soak_v1,
    evaluate_step12_v1,
)


def test_fix7_admin_metric_truth_wired() -> None:
    ok, detail = evaluate_fix7_admin_metric_truth_v1()
    assert ok is True, detail


def test_fix6_caps_snapshot() -> None:
    ok, detail, caps = evaluate_fix6_github_ingest_caps_v1()
    assert ok is True
    assert "cortex_github_prs_max_pages_per_repo" in caps
    assert detail


def test_l6_passes_with_completed_synthesis_artifact() -> None:
    ok, detail, checks = evaluate_l6_synthesis_legality_v1(
        phase_08_status="completed",
        phase_08_output={"jobs_completed": 2, "artifact_digests": ["sha256:abc"]},
        synthesis_legality_class="synthesis_partial",
        artifact_body={
            "synthesis_omission_rows": [{"sd_code": "SD-SCOPE-EMPTY"}],
            "synthesis_citations": [{"citation_id": "cite-0001"}],
        },
        jobs_completed=2,
        artifact_count=1,
    )
    assert ok is True, (detail, checks)


def test_l6_fails_when_forbidden() -> None:
    ok, _, checks = evaluate_l6_synthesis_legality_v1(
        phase_08_status="completed",
        phase_08_output={},
        synthesis_legality_class="synthesis_forbidden",
        artifact_body={},
    )
    assert ok is False
    assert checks["legality_not_forbidden"] is False


def test_p2_soak_starts_clock_on_motion() -> None:
    soak = evaluate_p2_autonomous_soak_v1(
        phase_cursor="phase_02_canonical",
        last_canonical_outcome="partial_progress",
        drainable_routable_estimate=100,
        untreated_routable_estimate=500,
        soak_captured_at="2026-05-22T12:00:00+00:00",
    )
    assert soak["p2_soak_t0_captured"] is True
    assert soak["track_b_soak_hours_required"] == TRACK_B_SOAK_HOURS_REQUIRED_V1


def test_step12_aggregate_passes() -> None:
    out = evaluate_step12_v1(
        phase_08_status="completed",
        phase_08_output={
            "jobs_completed": 1,
            "artifact_digests": ["sha256:step12-test"],
            "sd_rollup": {"SD-SCOPE-EMPTY": 1},
        },
        synthesis_legality_class="synthesis_partial",
        artifact_body={"synthesis_omission_rows": [{"sd_code": "SD-X"}]},
        jobs_completed=1,
        artifact_count=1,
        synthesis_job_receipt={"receipt_digest": "sha256:receipt-test"},
        lease_last_canonical_outcome="partial_progress",
        forward_progress_metrics={"drainable_routable_estimate": 0, "untreated_routable_estimate": 10},
        soak_captured_at="2026-05-22T12:00:00+00:00",
    )
    assert out["fix7_pass"] is True
    assert out["step12_pass"] is True
    assert out["level_6_met"] is True
