"""Unit tests for phase 1 text patterns."""

from __future__ import annotations

from vector.domains.cortex.graph.extractors.patterns import LINEAR_IDENTIFIER_RE


def test_linear_identifier_pattern() -> None:
    matches = LINEAR_IDENTIFIER_RE.findall("Fixes LIN-482 and LIN-1")
    assert "LIN-482" in matches
    assert "LIN-1" in matches
