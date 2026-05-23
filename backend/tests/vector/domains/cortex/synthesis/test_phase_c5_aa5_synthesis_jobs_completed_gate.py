"""Phase C5 — AA5 synthesis jobs_completed gate."""

from __future__ import annotations

import pytest

from vector.domains.cortex.synthesis.phase_c5_aa5_synthesis_jobs_completed_gate import (
    evaluate_aa5_synthesis_jobs_completed_gate_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_COMPLETED_EMPTY,
)


def test_aa5_pass_when_jobs_completed() -> None:
    gate = evaluate_aa5_synthesis_jobs_completed_gate_v1(
        {"jobs_completed": 2, "scope_empty": False},
        phase_08_started_at="2026-05-23T00:00:00+00:00",
        phase_08_status="completed",
    )
    assert gate["verdict"] == "PASS"
    assert gate["detail"] == "synthesis_jobs_completed"


def test_aa5_fail_started_only_under_strict(monkeypatch) -> None:
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase_c5_aa5_synthesis_jobs_completed_gate."
        "is_aa5_require_jobs_completed_enabled_v1",
        lambda: True,
    )
    gate = evaluate_aa5_synthesis_jobs_completed_gate_v1(
        {
            "jobs_completed": 0,
            "scope_empty": False,
            "retrieval_entries_in_epoch": 100,
        },
        phase_08_started_at="2026-05-23T00:00:00+00:00",
        phase_08_status="failed",
    )
    assert gate["verdict"] == "FAIL"
    assert gate["detail"] == "phase_08_started_without_jobs_completed"
    assert gate["evidence"]["fake_started_only_would_pass_legacy"] is True


def test_aa5_advisory_started_only_when_strict_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase_c5_aa5_synthesis_jobs_completed_gate."
        "is_aa5_require_jobs_completed_enabled_v1",
        lambda: False,
    )
    gate = evaluate_aa5_synthesis_jobs_completed_gate_v1(
        {"jobs_completed": 0, "scope_empty": False},
        phase_08_started_at="2026-05-23T00:00:00+00:00",
    )
    assert gate["verdict"] == "ADVISORY"
    assert "legacy" in gate["detail"]


def test_aa5_pass_lawful_empty() -> None:
    gate = evaluate_aa5_synthesis_jobs_completed_gate_v1(
        {
            "jobs_completed": 0,
            "scope_empty": True,
            "retrieval_entries_in_epoch": 0,
            "phase_08_outcome": PHASE_OUTCOME_COMPLETED_EMPTY,
            "empty_scope_reason": "no_published_index_epoch",
        },
        phase_08_started_at="2026-05-23T00:00:00+00:00",
    )
    assert gate["verdict"] == "PASS"
    assert gate["detail"] == "lawful_empty_synthesis"
