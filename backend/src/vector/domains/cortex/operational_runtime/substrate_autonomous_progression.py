"""Phase 08.5 P085-06 — autonomous phase progression (**G-P085-PROG-01**, **PIPE-085-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-substrate-continuity-doctrine.md`` §Autonomous progression.
Runtime wiring: ``vector.domains.cortex.substrate_pipeline.orchestrator``.
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_continuity import (
    assert_phase06_must_persist_waiting_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_WAITING,
    WAITING_ON_TCRE_COMPLETION,
    get_continuation_for_pipeline_v1,
)

PHASE085_AUTONOMOUS_PROGRESSION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_AUTONOMOUS_PROGRESSION_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-substrate-continuity-doctrine.md"
)

GP085_PROG01_GATE_ID_V1: Final[str] = "G-P085-PROG-01"
PIPE085_CHAIN_RULE_ID_V1: Final[str] = "PIPE-085-01"

PROGRESSION_LAW_IDS_V1: Final[tuple[str, ...]] = (
    "PROG-02-05-CHAIN",
    "PROG-06-WAIT",
    "PROG-TCRE-RESUME",
    "PROG-07-PUBLISH",
    "PROG-08-COMPLETE",
    "PIPE-085-01",
)


class SubstrateProgressionError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def build_autonomous_progression_catalog_v1() -> dict[str, Any]:
    """Doctrine catalog for autonomous progression (P085-06)."""
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_autonomous_progression_runtime_schema_version": int(
            PHASE085_AUTONOMOUS_PROGRESSION_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_AUTONOMOUS_PROGRESSION_SPEC_REF_V1,
        "primary_gate_id": GP085_PROG01_GATE_ID_V1,
        "pipe_rule_id": PIPE085_CHAIN_RULE_ID_V1,
        "progression_law_ids": list(PROGRESSION_LAW_IDS_V1),
        "substrate_pipeline_phase_order": list(SUBSTRATE_PIPELINE_PHASE_ORDER),
        "synchronous_chain_phases": [PHASE_02_CANONICAL, PHASE_03_IDENTITY, PHASE_04_GRAPH, PHASE_05_TRAVERSAL],
        "async_wait_phase": PHASE_06_TCRE,
        "waiting_on": WAITING_ON_TCRE_COMPLETION,
        "orchestrator_symbols": {
            "enqueue_next_pipeline_phase_v1": "vector.domains.cortex.substrate_pipeline.orchestrator",
            "on_tcre_job_completed_for_pipeline_v1": "vector.domains.cortex.substrate_pipeline.orchestrator",
            "on_retrieval_publish_completed_for_pipeline_v1": (
                "vector.domains.cortex.substrate_pipeline.orchestrator"
            ),
            "resume_pipeline_after_tcre_completion_v1": (
                "vector.domains.cortex.substrate_pipeline.pipeline_continuation"
            ),
            "mark_continuation_completed_v1": (
                "vector.domains.cortex.substrate_pipeline.pipeline_continuation"
            ),
        },
        "progression_steps": [
            {
                "law_id": "PROG-02-05-CHAIN",
                "description": "Phases 02–08 run inline under execution slice (M6; no Celery phase chain).",
            },
            {
                "law_id": "PROG-06-WAIT",
                "description": "Phase 06 persists WAITING / TCRE_COMPLETION before returning.",
            },
            {
                "law_id": "PROG-TCRE-RESUME",
                "description": "TCRE completion uses resume_pipeline_after_tcre_completion_v1.",
            },
            {
                "law_id": "PROG-07-PUBLISH",
                "description": "Phase 07 completion calls on_retrieval_publish_completed_for_pipeline_v1.",
            },
            {
                "law_id": "PROG-08-COMPLETE",
                "description": "Phase 08 completion calls mark_continuation_completed_v1.",
            },
            {
                "law_id": PIPE085_CHAIN_RULE_ID_V1,
                "description": "Phase 06 stops inline chain; TCRE resume uses execution slice at phase 07.",
            },
        ],
    }


def assert_pipe085_chain_after_phase06_legal_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> None:
    """**PIPE-085-01** — None chain after TCRE requires durable WAITING continuation."""
    continuation = get_continuation_for_pipeline_v1(session, pipeline_run_id=pipeline_run_id)
    if continuation is None:
        raise SubstrateProgressionError(
            "pipe085_missing_continuation_after_phase06",
            detail={"pipeline_run_id": str(pipeline_run_id)},
        )
    assert_phase06_must_persist_waiting_v1(
        continuation_present=True,
        waiting_on=continuation.waiting_on,
    )
    if continuation.continuation_status != CONTINUATION_STATUS_WAITING:
        raise SubstrateProgressionError(
            "pipe085_phase06_continuation_not_waiting",
            detail={
                "continuation_status": continuation.continuation_status,
                "expected": CONTINUATION_STATUS_WAITING,
            },
        )


def assert_tcre_completion_uses_resume_path_v1(
    *,
    has_tcre_job_id: bool,
    pipeline_scope: bool,
) -> None:
    """**PROG-TCRE-RESUME** — pipeline-scoped TCRE completion must not ad-hoc enqueue phase 07."""
    if pipeline_scope and not has_tcre_job_id:
        raise SubstrateProgressionError(
            "tcre_pipeline_resume_requires_job_id",
            detail={"required": "resume_pipeline_after_tcre_completion_v1"},
        )


def enforce_phase06_progression_law_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    phase06_output: Mapping[str, Any],
) -> None:
    """After phase 06 enqueue, require durable WAITING continuation (**PROG-06-WAIT**)."""
    _ = tenant_id
    if not phase06_output.get("async"):
        raise SubstrateProgressionError(
            "phase06_must_be_async",
            detail={"output": dict(phase06_output)},
        )
    job_id = phase06_output.get("job_id")
    if not job_id:
        raise SubstrateProgressionError(
            "phase06_missing_tcre_job_id",
            detail={"required": "enqueue_reconstruction_job_v1.job_id"},
        )
    assert_pipe085_chain_after_phase06_legal_v1(session, pipeline_run_id=pipeline_run_id)


def verify_gp085_prog01_progression_static() -> dict[str, Any]:
    """Static **G-P085-PROG-01** verification (symbols + catalog)."""
    errors: list[str] = []
    cat = build_autonomous_progression_catalog_v1()
    if set(cat["progression_law_ids"]) != set(PROGRESSION_LAW_IDS_V1):
        errors.append("progression_law_ids_mismatch")
    if cat["primary_gate_id"] != GP085_PROG01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    from vector.domains.cortex.substrate_pipeline import orchestrator as orch_mod
    from vector.domains.cortex.substrate_pipeline import pipeline_continuation as cont_mod

    for name in (
        "enqueue_next_pipeline_phase_v1",
        "on_tcre_job_completed_for_pipeline_v1",
        "on_retrieval_publish_completed_for_pipeline_v1",
    ):
        if not callable(getattr(orch_mod, name, None)):
            errors.append(f"missing_orchestrator_symbol:{name}")

    if hasattr(orch_mod, "chain_after_phase_v1"):
        errors.append("chain_after_phase_v1_must_be_removed_m6")

    enqueue_src = inspect.getsource(orch_mod.enqueue_next_pipeline_phase_v1)
    if "enqueue_execution_slice_at_phase_v1" not in enqueue_src:
        errors.append("enqueue_next_missing_execution_slice_redirect")

    tcre_src = inspect.getsource(orch_mod.on_tcre_job_completed_for_pipeline_v1)
    if (
        "resume_pipeline_after_tcre_completion_v1" not in tcre_src
        and "on_tcre_completed_for_convergence_v1" not in tcre_src
    ):
        errors.append("on_tcre_missing_resume_path")
    if "assert_tcre_completion_uses_resume_path_v1" not in tcre_src:
        errors.append("on_tcre_missing_resume_path_guard")

    if not callable(getattr(cont_mod, "resume_pipeline_after_tcre_completion_v1", None)):
        errors.append("missing_resume_pipeline_after_tcre_completion_v1")
    if not callable(getattr(cont_mod, "mark_continuation_completed_v1", None)):
        errors.append("missing_mark_continuation_completed_v1")

    from vector.domains.cortex.synthesis import synthesis_pipeline as syn_mod

    syn_src = inspect.getsource(syn_mod.run_substrate_phase_08_synthesis_v1)
    if "mark_continuation_completed_v1" not in syn_src:
        errors.append("phase08_runner_missing_mark_continuation_completed")

    from vector.domains.cortex.substrate_pipeline import phase_runners as runners_mod

    p07_src = inspect.getsource(runners_mod.run_phase_07_retrieval_v1)
    if "run_synthesis_activation_after_phase07_v1" not in p07_src:
        errors.append("phase07_runner_missing_synthesis_activation_hook")
    if "mark_continuation_completed_v1" in p07_src:
        errors.append("phase07_runner_must_not_mark_continuation_completed")

    p06_src = inspect.getsource(runners_mod.run_phase_06_tcre_v1)
    if "enforce_phase06_progression_law_v1" not in p06_src:
        errors.append("phase06_runner_missing_progression_enforcement")

    passed = not errors
    return {
        "id": GP085_PROG01_GATE_ID_V1,
        "name": "cesp_autonomous_phase_progression",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
