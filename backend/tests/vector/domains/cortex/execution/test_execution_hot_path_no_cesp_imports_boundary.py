"""CESP doctrine frozen off execution / phase runner hot path."""

from __future__ import annotations

import inspect

from vector.domains.cortex.execution.scheduling import verify_execution_hot_path_no_cesp_imports_boundary_v1
from vector.domains.cortex.execution import run_tenant_execution as exec_mod
from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod
from vector.domains.cortex.synthesis import synthesis_pipeline as syn_mod


def test_verify_execution_hot_path_no_cesp_imports_boundary() -> None:
    assert verify_execution_hot_path_no_cesp_imports_boundary_v1() == []


def test_phase06_imports_execution_contract_not_cesp() -> None:
    src = inspect.getsource(pr_mod.run_phase_06_tcre_v1)
    assert "execution.phase06_contract" in src
    assert "operational_runtime" not in src


def test_run_tenant_execution_imports_execution_contract_not_cesp() -> None:
    src = inspect.getsource(exec_mod.run_tenant_execution_v1)
    assert "execution.phase06_contract" in src
    assert "operational_runtime" not in src


def test_phase08_synthesis_imports_activation_gate_not_cesp() -> None:
    src = inspect.getsource(syn_mod.run_substrate_phase_08_synthesis_v1)
    assert "phase08_activation_gate" in src
    assert "operational_runtime" not in src
