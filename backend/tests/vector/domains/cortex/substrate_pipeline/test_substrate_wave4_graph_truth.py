"""Wave 4 — graph truth KPIs on phase 04, substrate walk skip, people clusters."""

from __future__ import annotations

import inspect

import pytest

from vector.domains.cortex.execution.execution_event_triggers import is_substrate_walk_schedule_skipped_v1
from vector.domains.cortex.execution.scheduling import verify_wave4_graph_truth_v1
from vector.domains.cortex.substrate_pipeline.constants import PHASE_04_GRAPH
from vector.domains.cortex.substrate_pipeline.graph_truth_metrics_v1 import (
    snapshot_graph_substrate_isolation_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    extract_phase_receipt_detail_v1,
)


def test_verify_wave4_graph_truth_v1() -> None:
    assert verify_wave4_graph_truth_v1() == []


def test_substrate_skip_walk_schedule_defaults_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORTEX_SUBSTRATE_SKIP_WALK_SCHEDULE_V1", raising=False)
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        assert is_substrate_walk_schedule_skipped_v1() is True
    finally:
        get_settings.cache_clear()


def test_phase04_runner_passes_prior_hash() -> None:
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    src = inspect.getsource(pr_mod.run_phase_04_graph_v1)
    assert "prior_graph_projection_stable_hash" in src
    assert "prior_isolated_pct" in src


def test_trigger_graph_hash_respects_substrate_skip() -> None:
    from vector.domains.cortex.execution import execution_event_triggers as et_mod

    src = inspect.getsource(et_mod.trigger_graph_hash_walk_schedule_v1)
    assert "is_substrate_walk_schedule_skipped_v1" in src
    assert "substrate_skip_walk_schedule_v1" in src


def test_phase04_receipt_detail_wave4_shape() -> None:
    detail = extract_phase_receipt_detail_v1(
        PHASE_04_GRAPH,
        {
            "graph_projection_stable_hash_sha256": "abc",
            "projection_hash_changed": True,
            "isolated_pct": 12.5,
            "isolated_pct_delta": 1.0,
            "node_count": 7000,
        },
    )
    assert detail["projection_hash_changed"] is True
    assert detail["isolated_pct"] == 12.5
    assert "node_count" not in detail


def test_snapshot_graph_substrate_isolation_module_exports() -> None:
    assert callable(snapshot_graph_substrate_isolation_v1)
