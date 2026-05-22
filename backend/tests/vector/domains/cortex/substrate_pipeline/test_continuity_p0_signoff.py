"""Phase 0 step 0.6 — P0 sign-off evaluator."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.substrate_pipeline.continuity_p0_signoff import (
    verify_p0_d_ci_gates_v1,
)

REPO_ROOT = Path(__file__).resolve().parents[6]


def test_p0_d_ci_gates_present_in_repo() -> None:
    out = verify_p0_d_ci_gates_v1(repo_root=REPO_ROOT)
    assert out["p0_d_pass"] is True
    assert out["checks"]["deploy_workflow_walk_policy_test"] is True
    assert out["checks"]["bundled_schema_present"] is True
