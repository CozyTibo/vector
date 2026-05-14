"""OCTS **STAGE-Z** static gates (``phase-05-ci-enforcement-architecture.md`` — nightly / tenant track)."""

from vector.domains.cortex.traversal.verification_gates_catalog import run_octs_wired_verification_stages_v1


def test_octs_verification_stage_z_passes() -> None:
    out = run_octs_wired_verification_stages_v1(("Z",))
    assert out["passed"] is True, out
