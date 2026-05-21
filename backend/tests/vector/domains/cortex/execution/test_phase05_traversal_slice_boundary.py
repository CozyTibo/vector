"""Phase 05 collapsed traversal slice (no schedule pass / explainability)."""

from __future__ import annotations

import inspect

from vector.domains.cortex.execution.scheduling import verify_phase05_traversal_slice_boundary_v1
from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod
from vector.domains.cortex.substrate_pipeline import substrate_traversal_execution as ste_mod


def test_verify_phase05_traversal_slice_boundary() -> None:
    assert verify_phase05_traversal_slice_boundary_v1() == []


def test_phase05_runner_calls_collapsed_traversal_slice_only() -> None:
    src = inspect.getsource(pr_mod.run_phase_05_traversal_v1)
    assert src.count("run_traversal_slice_for_pipeline_v1(") == 1
    assert "run_octs_walk_schedule_pass_v1" not in src
    assert "run_substrate_traversal_materialization_v1" not in src
    assert "octs_walk_schedule" not in src
    assert "traversal_explainability_panel" not in src


def test_traversal_slice_helper_sorts_starts_and_materializes() -> None:
    pick_src = inspect.getsource(ste_mod._pick_start_node_ids_v1)
    assert ".sort()" in pick_src
    slice_src = inspect.getsource(ste_mod.run_traversal_slice_for_pipeline_v1)
    assert "_pick_start_node_ids_v1" in slice_src
    assert "run_substrate_traversal_materialization_v1" in slice_src
    assert "traversal_explainability_panel" not in slice_src
