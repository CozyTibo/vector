"""P0 step 7 — determinism repair must not run on phase 02 execution hot path."""

from __future__ import annotations

import inspect

from vector.domains.cortex.execution import admin_commands as cmd_mod
from vector.domains.cortex.execution.scheduling import verify_p0_step7_determinism_repair_off_hot_path_v1
from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod


def test_verify_p0_step7_determinism_repair_off_hot_path() -> None:
    assert verify_p0_step7_determinism_repair_off_hot_path_v1() == []


def test_phase02_runner_has_no_inline_determinism_repair() -> None:
    src = inspect.getsource(pr_mod.run_phase_02_canonical_v1)
    assert "repair_tenant_materialization_oracle_determinism_drift" not in src
    assert "determinism_repair" not in src


def test_admin_execution_exposes_determinism_repair_hook() -> None:
    assert callable(cmd_mod.run_canonical_determinism_repair_v1)
    rerun_src = inspect.getsource(cmd_mod.execution_rerun_v1)
    assert "run_determinism_repair" in rerun_src
    assert "run_canonical_determinism_repair_v1" in rerun_src
