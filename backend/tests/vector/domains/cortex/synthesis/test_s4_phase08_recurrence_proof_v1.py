"""S4.6 — AA5 useful artifact + semantic panel claims metric."""

from __future__ import annotations

from vector.domains.cortex.synthesis.phase_c5_aa5_synthesis_jobs_completed_gate import (
    evaluate_aa5_synthesis_jobs_completed_gate_v1,
)


def test_aa5_requires_useful_artifact_when_jobs_completed() -> None:
    fail = evaluate_aa5_synthesis_jobs_completed_gate_v1(
        {"jobs_completed": 2, "useful_artifacts_published": 0, "scope_empty": False},
        phase_08_started_at="2026-01-01T00:00:00+00:00",
        phase_08_status="completed",
    )
    assert fail["verdict"] == "FAIL"
    assert fail["detail"] == "synthesis_jobs_completed_without_useful_artifact"

    ok = evaluate_aa5_synthesis_jobs_completed_gate_v1(
        {"jobs_completed": 1, "useful_artifacts_published": 1, "scope_empty": False},
        phase_08_started_at="2026-01-01T00:00:00+00:00",
        phase_08_status="completed",
    )
    assert ok["verdict"] == "PASS"
    assert ok["detail"] == "synthesis_jobs_completed_with_useful_artifact"


def test_aa5_lawful_empty_still_passes() -> None:
    out = evaluate_aa5_synthesis_jobs_completed_gate_v1(
        {
            "jobs_completed": 0,
            "useful_artifacts_published": 0,
            "scope_empty": True,
            "empty_scope_reason": "retrieval_empty",
            "retrieval_entries_in_epoch": 0,
        },
        phase_08_started_at="2026-01-01T00:00:00+00:00",
        phase_08_status="completed",
    )
    assert out["verdict"] == "PASS"
    assert out["detail"] == "lawful_empty_synthesis"
