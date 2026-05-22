"""Step 6 A3 validation helpers."""

from __future__ import annotations

from vector.domains.cortex.unlock.step06_candidate_regen import evaluate_a3_candidate_links_v1


def test_a3_passes_wedge_minimum() -> None:
    ok, detail = evaluate_a3_candidate_links_v1(candidate_count=120, candidates_persisted=120)
    assert ok is True
    assert "50" in detail


def test_a3_passes_at_cap() -> None:
    ok, _ = evaluate_a3_candidate_links_v1(candidate_count=2000, candidates_persisted=2000)
    assert ok is True


def test_a3_fails_empty() -> None:
    ok, detail = evaluate_a3_candidate_links_v1(candidate_count=0, candidates_persisted=0)
    assert ok is False
    assert "below wedge" in detail
