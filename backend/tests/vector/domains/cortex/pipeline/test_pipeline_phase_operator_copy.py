"""Operator copy for pipeline overview."""

from vector.domains.cortex.pipeline.pipeline_phase_operator_copy import (
    humanize_blocker_line,
    humanize_phase_issues,
    phase_status_label,
)


def test_phase_status_label() -> None:
    assert phase_status_label("healthy") == "Healthy"
    assert phase_status_label("waiting") == "Waiting"
    assert phase_status_label("degraded") == "Has gaps"


def test_humanize_canonical_backlog() -> None:
    assert "canonical" in humanize_blocker_line("canonical_backlog_unmaterialized: 24").lower()
    assert "24" in humanize_blocker_line("canonical_backlog_unmaterialized: 24")


def test_humanize_phase_issues_waiting_backlog() -> None:
    issues = humanize_phase_issues(
        operator_phase="canonical",
        status="waiting",
        blockers=[],
        backlog_count=100,
    )
    assert len(issues) == 1
    assert "100" in issues[0]
