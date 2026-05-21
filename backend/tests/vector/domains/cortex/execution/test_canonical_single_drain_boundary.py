"""Phase 02 must use a single drain_forward_progress_backlog entry."""

from __future__ import annotations

import inspect

from vector.domains.cortex.execution.scheduling import verify_canonical_single_drain_boundary_v1
from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod


def test_verify_canonical_single_drain_boundary() -> None:
    assert verify_canonical_single_drain_boundary_v1() == []


def test_phase02_runner_single_forward_progress_drain() -> None:
    src = inspect.getsource(pr_mod.run_phase_02_canonical_v1)
    assert "drain_stub_materialize_backlog" not in src
    assert "slack_preface" not in src
    assert src.count("drain_forward_progress_backlog(") == 1
