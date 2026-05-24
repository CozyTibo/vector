"""S4.2 — single pipeline synthesis path wiring."""

from __future__ import annotations

from vector.domains.cortex.synthesis.synthesis_pipeline_path_v1 import (
    verify_synthesis_pipeline_single_path_v1,
)


def test_s4_pipeline_single_path_static() -> None:
    wiring = verify_synthesis_pipeline_single_path_v1()
    assert wiring["wiring_ok"] is True
    assert wiring["errors"] == []
    assert wiring["pipeline_path_kind"] == "inline_per_island_v1"
