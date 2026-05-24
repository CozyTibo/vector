"""S4.2 — single pipeline synthesis path (inline per-island only)."""

from __future__ import annotations

import inspect
from typing import Any, Final

SYNTHESIS_PIPELINE_PATH_SCHEMA_VERSION: Final[int] = 1
S4_PIPELINE_PATH_STEP: Final[str] = "s4_2_single_pipeline_synthesis_path"
PIPELINE_SYNTHESIS_PATH_KIND_V1: Final[str] = "inline_per_island_v1"
CELERY_SYNTHESIS_JOB_TASK_ADMIN_ONLY_V1: Final[str] = "admin_ad_hoc_only"


class SynthesisPipelinePathError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def verify_synthesis_pipeline_single_path_v1() -> dict[str, Any]:
    """Static proof: pipeline materialize is per-island only; Celery job task is admin-only."""
    from vector.domains.cortex.synthesis import synthesis_pipeline as sp
    from vector.domains.cortex.synthesis.synthesis_per_island import materialize_synthesis_per_island_v1

    errors: list[str] = []
    mat_src = inspect.getsource(sp.materialize_synthesis_for_pipeline_v1)
    if "materialize_synthesis_per_island_v1" not in mat_src:
        errors.append("materialize_missing_per_island_entrypoint")
    if "iter_pipeline_synthesis_scopes_v1" in mat_src:
        errors.append("global_pipeline_scope_iterator_still_on_hot_path")
    if "execute_synthesis_job_envelope_v1" in mat_src:
        errors.append("global_inline_orchestrator_still_on_hot_path")

    pi_src = inspect.getsource(materialize_synthesis_per_island_v1)
    if "per_island_mode" not in pi_src:
        errors.append("per_island_materialize_missing_mode_flag")

    from app.tasks import cortex_synthesis_jobs as celery_mod

    task_doc = str(celery_mod.__doc__ or "")
    if "admin" not in task_doc.lower() and "ad-hoc" not in task_doc.lower():
        errors.append("celery_synthesis_job_task_missing_admin_only_doc")

    return {
        "schema_version": SYNTHESIS_PIPELINE_PATH_SCHEMA_VERSION,
        "step": S4_PIPELINE_PATH_STEP,
        "pipeline_path_kind": PIPELINE_SYNTHESIS_PATH_KIND_V1,
        "celery_job_task_policy": CELERY_SYNTHESIS_JOB_TASK_ADMIN_ONLY_V1,
        "wiring_ok": not errors,
        "errors": errors,
    }
