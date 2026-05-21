"""P0 step 2 — TCRE Celery worker must not materialize retrieval (phase 07 only)."""

from __future__ import annotations

import inspect
from pathlib import Path

from vector.domains.cortex.execution.scheduling import (
    verify_p0_step2_phase06_tcre_worker_boundary_v1,
)


def test_verify_p0_step2_phase06_tcre_worker_boundary() -> None:
    assert verify_p0_step2_phase06_tcre_worker_boundary_v1() == []


def test_tcre_celery_task_has_no_retrieval_side_effects() -> None:
    import app.tasks.cortex_tcre_reconstruction_jobs as tcre_jobs

    src = inspect.getsource(tcre_jobs.run_tcre_reconstruction_job_task)
    assert "materialize_retrieval" not in src
    assert "on_tcre_job_completed_for_pipeline_v1" in src


def test_incremental_after_tcre_helper_removed() -> None:
    from vector.domains.cortex.retrieval import retrieval_index_materialization as rim

    assert not hasattr(rim, "materialize_retrieval_index_incremental_after_tcre_v1")
    src = Path(inspect.getsourcefile(rim) or "").read_text(encoding="utf-8")
    assert "materialize_retrieval_index_incremental_after_tcre_v1" not in src
