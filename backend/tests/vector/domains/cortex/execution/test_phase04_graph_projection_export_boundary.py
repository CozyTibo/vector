"""Phase 04 direct graph projection export (no replay job / verification slice)."""

from __future__ import annotations

import inspect

from vector.domains.cortex.execution.scheduling import verify_phase04_graph_projection_export_boundary_v1
from vector.domains.cortex.identity import projection_export as pe_mod
from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod


def test_verify_phase04_graph_projection_export_boundary() -> None:
    assert verify_phase04_graph_projection_export_boundary_v1() == []


def test_phase04_runner_calls_direct_export_only() -> None:
    src = inspect.getsource(pr_mod.run_phase_04_graph_v1)
    assert src.count("run_graph_projection_export_for_pipeline_v1(") == 1
    assert "execute_org_link_replay_job" not in src
    assert "graph_projection_export_job_id" not in src
    assert "build_org_graph_traversal_verification_slice_v1" not in src
    assert "org_graph_traversal_verification_slice" not in src


def test_graph_projection_export_pipeline_helper_uses_build_document() -> None:
    src = inspect.getsource(pe_mod.run_graph_projection_export_for_pipeline_v1)
    assert "build_org_graph_projection_export_document" in src
    assert "graph_projection_stable_hash_sha256" in src
    assert "node_count" in src
    assert "edge_count" in src
