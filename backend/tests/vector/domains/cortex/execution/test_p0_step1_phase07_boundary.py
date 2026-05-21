"""P0 step 1 — phase 07 retrieval must not run synthesis activation."""

from __future__ import annotations

import inspect

from vector.domains.cortex.execution.scheduling import verify_p0_step1_phase07_retrieval_boundary_v1
from vector.domains.cortex.substrate_pipeline import phase_runners as pr


def test_verify_p0_step1_phase07_retrieval_boundary() -> None:
    assert verify_p0_step1_phase07_retrieval_boundary_v1() == []


def test_phase07_runner_returns_retrieval_output_only() -> None:
    src = inspect.getsource(pr.run_phase_07_retrieval_v1)
    assert "run_synthesis_activation_after_phase07_v1" not in src
    assert "next_phase_chain" not in src
    assert "return out" in src
