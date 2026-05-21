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

from vector.domains.cortex.execution.phase06_contract import (
    ExecutionProgressionError as _ExecutionProgressionError,
    assert_pipe085_chain_after_phase06_legal_v1,
    enforce_phase06_progression_law_v1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_08_SYNTHESIS,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import WAITING_ON_TCRE_COMPLETION

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


SubstrateProgressionError = _ExecutionProgressionError


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
                "description": "Phase 06 enqueues async TCRE; execution worker marks lease AWAITING_TCRE.",
            },
            {
                "law_id": "PROG-TCRE-RESUME",
                "description": "TCRE completion uses on_tcre_job_terminal_for_execution_v1 (execution lease only).",
            },
            {
                "law_id": "PROG-07-PUBLISH",
                "description": "Phase 07 completion calls on_retrieval_publish_completed_for_pipeline_v1.",
            },
            {
                "law_id": "PROG-08-COMPLETE",
                "description": "Phase 08 completes via phase_runs + pipeline finalize (no continuation writes).",
            },
            {
                "law_id": PIPE085_CHAIN_RULE_ID_V1,
                "description": "Phase 06 stops inline chain; TCRE resume uses execution slice at phase 07.",
            },
        ],
    }


def assert_tcre_completion_uses_resume_path_v1(
    *,
    has_tcre_job_id: bool,
    pipeline_scope: bool,
) -> None:
    """**PROG-TCRE-RESUME** — pipeline-scoped TCRE completion must not ad-hoc enqueue phase 07."""
    if pipeline_scope and not has_tcre_job_id:
        raise SubstrateProgressionError(
            "tcre_pipeline_resume_requires_job_id",
            detail={"required": "on_tcre_job_terminal_for_execution_v1"},
        )


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
    if "resume_pipeline_after_tcre_completion_v1" in tcre_src:
        errors.append("on_tcre_must_not_call_continuation_resume")
    if "on_tcre_job_terminal_for_execution_v1" not in tcre_src:
        errors.append("on_tcre_missing_execution_terminal_resume")
    if "assert_tcre_completion_uses_resume_path_v1" not in tcre_src:
        errors.append("on_tcre_missing_resume_path_guard")

    if not callable(getattr(cont_mod, "resume_pipeline_after_tcre_completion_v1", None)):
        errors.append("missing_resume_pipeline_after_tcre_completion_v1")
    if not callable(getattr(cont_mod, "mark_continuation_completed_v1", None)):
        errors.append("missing_mark_continuation_completed_v1")

    from vector.domains.cortex.synthesis import synthesis_pipeline as syn_mod

    syn_src = inspect.getsource(syn_mod.run_substrate_phase_08_synthesis_v1)
    if "mark_continuation_completed_v1" in syn_src:
        errors.append("phase08_runner_must_not_mark_continuation_completed")
    if "evaluate_synthesis_activation_schedule_v1" not in syn_src:
        errors.append("phase08_runner_missing_synthesis_activation_evaluation")

    from vector.domains.cortex.substrate_pipeline import phase_runners as runners_mod

    from vector.domains.cortex.execution.scheduling import (
        verify_tcre_worker_no_retrieval_materialization_boundary_v1,
        verify_single_tcre_execution_resume_boundary_v1,
        verify_execution_hot_path_no_continuation_boundary_v1,
        verify_canonical_single_drain_boundary_v1,
        verify_execution_lease_no_pass_fairness_boundary_v1,
        verify_canonical_no_inline_determinism_repair_boundary_v1,
        verify_phase03_identity_projection_boundary_v1,
        verify_phase04_graph_projection_export_boundary_v1,
        verify_phase05_traversal_slice_boundary_v1,
        verify_execution_hot_path_no_cesp_imports_boundary_v1,
    )

    errors.extend(verify_tcre_worker_no_retrieval_materialization_boundary_v1())
    errors.extend(verify_single_tcre_execution_resume_boundary_v1())
    errors.extend(verify_execution_hot_path_no_continuation_boundary_v1())
    errors.extend(verify_canonical_single_drain_boundary_v1())
    errors.extend(verify_execution_lease_no_pass_fairness_boundary_v1())
    errors.extend(verify_canonical_no_inline_determinism_repair_boundary_v1())
    errors.extend(verify_phase03_identity_projection_boundary_v1())
    errors.extend(verify_phase04_graph_projection_export_boundary_v1())
    errors.extend(verify_phase05_traversal_slice_boundary_v1())
    errors.extend(verify_execution_hot_path_no_cesp_imports_boundary_v1())

    p03_src = inspect.getsource(runners_mod.run_phase_03_identity_v1)
    if "finalize_identity_substrate_operator_audit" in p03_src:
        errors.append("phase03_runner_must_not_call_finalize_identity_substrate_operator_audit")
    if "run_identity_substrate_projection_for_pipeline_v1" not in p03_src:
        errors.append("phase03_runner_must_call_identity_projection_for_pipeline")

    p04_src = inspect.getsource(runners_mod.run_phase_04_graph_v1)
    if "execute_org_link_replay_job" in p04_src:
        errors.append("phase04_runner_must_not_call_org_link_replay_job")
    if "run_graph_projection_export_for_pipeline_v1" not in p04_src:
        errors.append("phase04_runner_must_call_graph_projection_export_for_pipeline")
    if "build_org_graph_traversal_verification_slice_v1" in p04_src:
        errors.append("phase04_runner_must_not_build_verification_slice")

    p05_src = inspect.getsource(runners_mod.run_phase_05_traversal_v1)
    if "run_octs_walk_schedule_pass_v1" in p05_src:
        errors.append("phase05_runner_must_not_call_octs_walk_schedule_pass")
    if "run_traversal_slice_for_pipeline_v1" not in p05_src:
        errors.append("phase05_runner_must_call_traversal_slice_for_pipeline")
    if "traversal_explainability_panel" in p05_src:
        errors.append("phase05_runner_must_not_export_explainability_panel")

    p02_src = inspect.getsource(runners_mod.run_phase_02_canonical_v1)
    if "drain_stub_materialize_backlog" in p02_src:
        errors.append("phase02_runner_must_not_call_drain_stub")
    if p02_src.count("drain_forward_progress_backlog(") != 1:
        errors.append("phase02_runner_must_single_drain_forward_progress")
    if "repair_tenant_materialization_oracle_determinism_drift" in p02_src:
        errors.append("phase02_runner_must_not_run_determinism_repair")

    p06_src = inspect.getsource(runners_mod.run_phase_06_tcre_v1)
    if "pipeline_continuation" in p06_src or "mark_pipeline_waiting_on_tcre_v1" in p06_src:
        errors.append("phase06_runner_must_not_write_pipeline_continuation")

    p07_src = inspect.getsource(runners_mod.run_phase_07_retrieval_v1)
    if "run_synthesis_activation_after_phase07_v1" in p07_src:
        errors.append("phase07_runner_must_not_call_synthesis_activation")
    if "mark_continuation_completed_v1" in p07_src:
        errors.append("phase07_runner_must_not_mark_continuation_completed")
    if "continue_substrate_operational_progression_v1" in p07_src:
        errors.append("phase07_runner_must_not_call_progression_coordinator_m7")

    import importlib.util

    if importlib.util.find_spec(
        "vector.domains.cortex.operational_runtime.substrate_operational_progression"
    ) is not None:
        errors.append("substrate_operational_progression_module_must_be_deleted_m7")

    from vector.domains.cortex.execution import admin_rerun as rerun_mod

    if not callable(getattr(rerun_mod, "admin_rerun_substrate_execution_v1", None)):
        errors.append("missing_admin_rerun_substrate_execution_v1")

    exec_src = inspect.getsource(rerun_mod.admin_rerun_substrate_execution_v1)
    if "enqueue_execution_slice_at_phase_v1" not in exec_src:
        errors.append("admin_rerun_missing_execution_slice_enqueue")

    p06_src = inspect.getsource(runners_mod.run_phase_06_tcre_v1)
    if "execution.phase06_contract" not in p06_src:
        errors.append("phase06_runner_must_import_execution_phase06_contract")
    if "operational_runtime" in p06_src:
        errors.append("phase06_runner_must_not_import_operational_runtime")
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
