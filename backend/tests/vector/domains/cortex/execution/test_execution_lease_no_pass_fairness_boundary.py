"""Execution lease must not persist canonical pass-fairness state."""

from __future__ import annotations

import inspect

from vector.domains.cortex.execution import run_tenant_execution as exec_mod
from vector.domains.cortex.execution.scheduling import verify_execution_lease_no_pass_fairness_boundary_v1
from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod


def test_verify_execution_lease_no_pass_fairness_boundary() -> None:
    assert verify_execution_lease_no_pass_fairness_boundary_v1() == []


def test_execution_worker_has_no_pass_fairness_helpers() -> None:
    src = inspect.getsource(exec_mod.run_tenant_convergence_v1)
    assert "_canonical_pass_index_from_lease" not in src
    assert "_store_canonical_pass_index_on_lease" not in src
    assert "_store_pass_fairness_on_lease" not in src
    assert "parse_pass_cooldown_until" not in src
    assert "_store_canonical_slice_outcome_on_lease" in src


def test_phase02_runner_has_no_pass_fairness_parameters() -> None:
    src = inspect.getsource(pr_mod.run_phase_02_canonical_v1)
    assert "pass_index: int" not in src
    assert "pass_cooldowns:" not in src
    assert "pass_stall_counts:" not in src
