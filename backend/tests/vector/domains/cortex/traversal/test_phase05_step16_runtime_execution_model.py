"""P05-16 — runtime execution model (**REM-01/02**, **FS-REM-01/02**, **G-P05-RT-01/02**)."""

from __future__ import annotations

import json

import pytest

from vector.domains.cortex.traversal.runtime_execution_model import (
    REM_RUNTIME_SCHEMA_VERSION,
    RuntimeExecutionModelError,
    list_fs_rem01_reference_walk_artifact_forbidden_keys_v1,
    octs_runtime_execution_fixture_dir,
    path_context_id_v1,
    run_reference_frontier_walk_v1,
    verify_gp05_rt01_engine_determinism_static,
    verify_gp05_rt02_frontier_cap_budget_static,
)


def test_rem_runtime_schema_version() -> None:
    assert REM_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp05_rt01_static_passes() -> None:
    out = verify_gp05_rt01_engine_determinism_static()
    assert out["id"] == "G-P05-RT-01"
    assert out["passed"] is True


def test_verify_gp05_rt02_static_passes() -> None:
    out = verify_gp05_rt02_frontier_cap_budget_static()
    assert out["id"] == "G-P05-RT-02"
    assert out["passed"] is True


def test_octs_runtime_execution_fixture_dir() -> None:
    d = octs_runtime_execution_fixture_dir()
    assert (d / "determinism_inner_v1.json").is_file()
    assert (d / "star_frontier_cap_inner_v1.json").is_file()


def test_list_fs_rem01_detects_nested_forbidden_key() -> None:
    bad = {"hops_emitted": 1, "async_neighbor_task_ids": []}
    hits = list_fs_rem01_reference_walk_artifact_forbidden_keys_v1(bad)
    assert any("FS-REM-01:forbidden_key" in h for h in hits)


def test_path_context_id_v1_stable() -> None:
    a = path_context_id_v1(("11111111-1111-1111-1111-111111111111",))
    b = path_context_id_v1(("11111111-1111-1111-1111-111111111111",))
    assert a == b
    assert a.startswith("sha256:")


def test_run_reference_frontier_walk_reaches_target_on_determinism_fixture() -> None:
    inner_path = octs_runtime_execution_fixture_dir() / "determinism_inner_v1.json"
    inner = json.loads(inner_path.read_text(encoding="utf-8"))
    r = run_reference_frontier_walk_v1(
        inner,
        start_node_id="11111111-1111-1111-1111-111111111111",
        target_node_id="22222222-2222-2222-2222-222222222222",
        max_hops=4,
        max_frontier=64,
        max_edges_visited=500,
        detect_cycles=True,
        stop_on_cycle=True,
    )
    assert r["termination_reason"] == "target_reached"
    assert r["hops_emitted"] >= 1
    assert not list_fs_rem01_reference_walk_artifact_forbidden_keys_v1(dict(r))


def test_run_reference_frontier_walk_invalid_projection_raises() -> None:
    with pytest.raises(RuntimeExecutionModelError):
        run_reference_frontier_walk_v1(
            {"nodes": [], "edges": "not-a-list"},
            start_node_id="11111111-1111-1111-1111-111111111111",
            target_node_id=None,
            max_hops=1,
            max_frontier=8,
            max_edges_visited=10,
            detect_cycles=True,
        )
