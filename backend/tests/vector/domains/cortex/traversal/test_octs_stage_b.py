"""OCTS **STAGE-B** unit oracle gates (``phase-05-ci-enforcement-architecture.md`` §2)."""

from __future__ import annotations

from vector.domains.cortex.traversal.verification_gates_catalog import (
    run_octs_wired_verification_stages_v1,
)


def test_octs_verification_stage_b_passes() -> None:
    out = run_octs_wired_verification_stages_v1(("B",))
    assert out["passed"] is True, out
