"""M6: single execution slice task; no legacy phase Celery chain."""

from __future__ import annotations

import inspect

from vector.domains.cortex.execution.scheduling import (
    CELERY_EXECUTION_SLICE_TASK_NAME_V1,
    verify_no_legacy_phase_chain_v1,
)


def test_execution_slice_task_name_constant() -> None:
    assert CELERY_EXECUTION_SLICE_TASK_NAME_V1 == "vector.cortex.execution.run_slice"


def test_verify_no_legacy_phase_chain_static_m6() -> None:
    assert verify_no_legacy_phase_chain_v1() == []


def test_orchestrator_has_no_chain_after_phase_v1() -> None:
    from vector.domains.cortex.substrate_pipeline import orchestrator as orch

    assert not hasattr(orch, "chain_after_phase_v1")


def test_enqueue_next_redirects_to_execution_slice() -> None:
    from vector.domains.cortex.substrate_pipeline import orchestrator as orch

    src = inspect.getsource(orch.enqueue_next_pipeline_phase_v1)
    assert "enqueue_execution_slice_at_phase_v1" in src
    assert "run_cortex_substrate_pipeline_phase_task" not in src
