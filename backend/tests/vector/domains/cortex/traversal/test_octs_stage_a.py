"""OCTS **STAGE-A** static gates (``phase-05-ci-enforcement-architecture.md`` §2)."""

from __future__ import annotations

from vector.domains.cortex.traversal.verification_gates_catalog import (
    run_octs_wired_verification_stages_v1,
)


def test_octs_verification_stage_a_passes() -> None:
    out = run_octs_wired_verification_stages_v1(("A",))
    assert out["passed"] is True, out
