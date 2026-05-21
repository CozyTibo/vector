"""Execution hot path must not write pipeline_continuation."""

from __future__ import annotations

import inspect

from vector.domains.cortex.execution.scheduling import (
    verify_execution_hot_path_no_continuation_boundary_v1,
)
from vector.domains.cortex.synthesis import synthesis_pipeline as syn_mod
from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod


def test_verify_execution_hot_path_no_continuation_boundary() -> None:
    assert verify_execution_hot_path_no_continuation_boundary_v1() == []


def test_phase06_runner_has_no_continuation_writes() -> None:
    src = inspect.getsource(pr_mod.run_phase_06_tcre_v1)
    assert "pipeline_continuation" not in src
    assert "mark_pipeline_waiting_on_tcre_v1" not in src


def test_phase08_runner_has_no_continuation_writes() -> None:
    src = inspect.getsource(syn_mod.run_substrate_phase_08_synthesis_v1)
    assert "mark_continuation_completed_v1" not in src
    assert "pipeline_continuation" not in src
