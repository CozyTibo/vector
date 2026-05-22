"""Step 7 A2 validation helpers."""

from __future__ import annotations

from vector.domains.cortex.unlock.step07_graph_density_promotion import (
    evaluate_a2_authoritative_links_v1,
)


def test_a2_passes_wedge_minimum() -> None:
    ok, detail = evaluate_a2_authoritative_links_v1(
        authoritative_links_active=12,
        promoted_count=12,
    )
    assert ok is True
    assert "1" in detail


def test_a2_passes_at_pass_cap() -> None:
    ok, _ = evaluate_a2_authoritative_links_v1(authoritative_links_active=200)
    assert ok is True


def test_a2_fails_empty() -> None:
    ok, detail = evaluate_a2_authoritative_links_v1(
        authoritative_links_active=0,
        promoted_count=0,
    )
    assert ok is False
    assert "below wedge" in detail
