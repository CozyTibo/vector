"""Tenant execution scheduling helpers (authoritative beat + ingest path)."""

from __future__ import annotations

import inspect
import os
from typing import Final

from vector.settings import Settings

CELERY_CONVERGENCE_SWEEP_BEAT_KEY_V1: Final[str] = "cortex-convergence-sweep"
CELERY_CONVERGENCE_SWEEP_TASK_NAME_V1: Final[str] = "vector.cortex.convergence.sweep"
CELERY_CONVERGENCE_RUN_TASK_NAME_V1: Final[str] = "vector.cortex.convergence.run_tenant"
CELERY_EXECUTION_SLICE_TASK_NAME_V1: Final[str] = "vector.cortex.execution.run_slice"


def _env_flag(name: str, *, default: str = "true") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes")


def convergence_runtime_authoritative_v1(settings: Settings | None = None) -> bool:
    """True when execution sweeper is enabled (sole periodic substrate scheduler after M3)."""
    if settings is None:
        return _env_flag("CORTEX_CONVERGENCE_SWEEPER_ENABLED")
    return bool(settings.cortex_convergence_sweeper_enabled)


execution_runtime_authoritative_v1 = convergence_runtime_authoritative_v1


LEGACY_SUBSTRATE_BEAT_TASK_NAMES_V1: Final[tuple[str, ...]] = (
    "vector.cortex.substrate_pipeline.continuity_watchdog",
    "vector.cortex.operational_runtime.substrate_progression_tick",
)


def verify_legacy_substrate_beats_absent_from_celery_beat_v1() -> list[str]:
    """Return error codes if legacy watchdog/progression ticks are still on Celery beat (M3)."""
    from app.celery_app import celery_app

    errors: list[str] = []
    beat = dict(celery_app.conf.beat_schedule or {})
    for task_name in LEGACY_SUBSTRATE_BEAT_TASK_NAMES_V1:
        for key, entry in beat.items():
            if str(entry.get("task")) == task_name:
                errors.append(f"legacy_substrate_beat_still_registered:{key}:{task_name}")
    return errors


def verify_convergence_sweep_in_celery_beat_v1() -> list[str]:
    """Return error codes if execution sweeper is not registered in beat schedule."""
    from app.celery_app import celery_app
    from app.tasks import cortex_execution as exec_mod

    errors: list[str] = []
    errors.extend(verify_no_legacy_phase_chain_v1())
    beat = dict(celery_app.conf.beat_schedule or {})
    entry = beat.get(CELERY_CONVERGENCE_SWEEP_BEAT_KEY_V1)
    if entry is None:
        errors.append("convergence_sweep_beat_missing")
    elif str(entry.get("task")) != CELERY_CONVERGENCE_SWEEP_TASK_NAME_V1:
        errors.append("convergence_sweep_beat_task_mismatch")

    slice_src = inspect.getsource(exec_mod.run_execution_slice_task)
    if "run_tenant_convergence_v1" not in slice_src:
        errors.append("execution_slice_task_missing_runner")
    errors.extend(verify_legacy_substrate_beats_absent_from_celery_beat_v1())
    errors.extend(verify_tenant_execution_fsm_on_lease_v1())
    errors.extend(verify_m9_dead_celery_modules_absent_v1())
    return errors


def verify_schedule_substrate_pipeline_uses_convergence_v1() -> list[str]:
    """Return error codes if legacy coordinator scheduling remains in orchestrator (M4)."""
    from vector.domains.cortex.substrate_pipeline import orchestrator as orch

    errors: list[str] = []
    src = inspect.getsource(orch.schedule_substrate_pipeline_v1)
    if "run_cortex_substrate_pipeline_coordinator_task" in src:
        errors.append("schedule_substrate_pipeline_enqueues_legacy_coordinator")
    if "enqueue_tenant_convergence_v1" not in src:
        errors.append("schedule_substrate_pipeline_missing_convergence_enqueue")
    if "mark_tenant_dirty_v1" not in src:
        errors.append("schedule_substrate_pipeline_missing_dirty_mark")
    return errors


def verify_tenant_execution_fsm_on_lease_v1() -> list[str]:
    """Return error codes if M5 FSM is not wired on execution lease (M5)."""
    from vector.domains.cortex.execution import lease as lease_mod

    errors: list[str] = []
    model_path = (
        "vector.infrastructure.db.models.cortex_tenant_convergence_lease."
        "CortexTenantConvergenceLease"
    )
    try:
        from vector.infrastructure.db.models.cortex_tenant_convergence_lease import (
            CortexTenantConvergenceLease,
        )
    except ImportError:
        errors.append("tenant_execution_lease_model_missing")
        return errors
    if not hasattr(CortexTenantConvergenceLease, "fsm_state"):
        errors.append("tenant_execution_lease_missing_fsm_state_column")
    dirty_src = inspect.getsource(lease_mod.mark_tenant_dirty_v1)
    if "apply_fsm_transition_v1" not in dirty_src:
        errors.append("mark_dirty_missing_fsm_transition")
    from vector.domains.cortex.execution import fsm as fsm_mod

    if "record_execution_transition_v1" not in inspect.getsource(fsm_mod):
        errors.append("fsm_missing_transition_log_writer")
    return errors


def verify_no_legacy_phase_chain_v1() -> list[str]:
    """Return error codes if M6 legacy phase chaining remains (M6)."""
    from vector.domains.cortex.substrate_pipeline import orchestrator as orch

    errors: list[str] = []
    if hasattr(orch, "chain_after_phase_v1"):
        errors.append("chain_after_phase_v1_still_exported")
    enqueue_src = inspect.getsource(orch.enqueue_next_pipeline_phase_v1)
    if "run_cortex_substrate_pipeline_phase_task" in enqueue_src:
        errors.append("enqueue_next_still_uses_phase_celery_task")
    if "enqueue_execution_slice_at_phase_v1" not in enqueue_src:
        errors.append("enqueue_next_missing_execution_slice_redirect")
    from vector.domains.cortex.execution import enqueue as enqueue_mod

    if "run_execution_slice_task" not in inspect.getsource(enqueue_mod.enqueue_tenant_convergence_v1):
        errors.append("enqueue_missing_execution_slice_task")
    return errors


M9_DEAD_CELERY_TASK_MODULES_V1: Final[tuple[str, ...]] = (
    "app.tasks.cortex_graph_density_promotion",
    "app.tasks.cortex_substrate_traversal_scheduling",
    "app.tasks.cortex_substrate_traversal_retry",
    "app.tasks.cortex_substrate_stalled_traversal_recovery",
    "app.tasks.cortex_orphan_continuity_stitch",
    "app.tasks.cortex_substrate_tcre_saturation_scheduling",
    "app.tasks.cortex_substrate_synthesis_activation_scheduling",
    "app.tasks.cortex_canonical_materialize_backlog",
    "app.tasks.cortex_post_ingestion_substrate_refresh",
    "app.tasks.cortex_substrate_continuity_watchdog",
    "app.tasks.cortex_full_pipeline_rerun",
    "app.tasks.cortex_substrate_pipeline",
)


M9_DEAD_CELERY_TASK_NAMES_V1: Final[tuple[str, ...]] = (
    "vector.cortex.operational_runtime.graph_density_promotion_pass",
    "vector.cortex.operational_runtime.schedule_octs_walks_for_tenant",
    "vector.cortex.operational_runtime.traversal_retry_and_heal_pass",
    "vector.cortex.operational_runtime.stalled_traversal_recovery_pass",
    "vector.cortex.operational_runtime.orphan_continuity_stitch_pass",
    "vector.cortex.operational_runtime.schedule_tcre_saturation_for_tenant",
    "vector.cortex.operational_runtime.schedule_synthesis_activation_for_tenant",
    "vector.cortex.canonical.drain_stub_materialize_backlog",
    "vector.cortex.post_ingestion_substrate_refresh",
    "vector.cortex.substrate_pipeline.continuity_watchdog",
    "vector.cortex.ingestion.flush_rerun_to_identity",
    "vector.cortex.substrate_pipeline.coordinator",
    "vector.cortex.substrate_pipeline.phase",
    "vector.cortex.substrate_pipeline.phase_08_synthesis",
)


def verify_m9_dead_celery_modules_absent_v1() -> list[str]:
    """Return error codes if M9 sidecar / legacy Celery task modules still exist (M9)."""
    import importlib.util

    from vector.domains.cortex.substrate_pipeline import phase_runners as pr

    errors: list[str] = []
    for mod in M9_DEAD_CELERY_TASK_MODULES_V1:
        if importlib.util.find_spec(mod) is not None:
            errors.append(f"dead_celery_module_still_present:{mod}")

    from app.celery_app import celery_app

    for task_name in M9_DEAD_CELERY_TASK_NAMES_V1:
        if task_name in celery_app.tasks:
            errors.append(f"dead_celery_task_still_registered:{task_name}")

    p04 = inspect.getsource(pr.run_phase_04_graph_v1)
    if "schedule_graph_density_pass_v1" in p04:
        errors.append("phase04_still_schedules_graph_density_sidecar")
    p05 = inspect.getsource(pr.run_phase_05_traversal_v1)
    if "schedule_octs_walks_for_tenant_v1" in p05:
        errors.append("phase05_still_schedules_celery_traversal_sidecar")
    if "run_octs_walk_schedule_pass_v1" not in p05:
        errors.append("phase05_missing_inline_traversal_pass")
    p06 = inspect.getsource(pr.run_phase_06_tcre_v1)
    if "run_tcre_saturation_after_phase06_v1" in p06:
        errors.append("phase06_still_runs_tcre_saturation_sidecar")

    from vector.domains.cortex.operational_runtime import substrate_traversal_scheduling as sts

    sched_src = inspect.getsource(sts.run_octs_walk_schedule_pass_v1)
    if "run_traversal_retry_and_heal_pass_v1" in sched_src:
        errors.append("traversal_pass_still_integrates_retry_sidecar")
    if "run_stalled_traversal_recovery_pass_v1" in sched_src:
        errors.append("traversal_pass_still_integrates_stall_recovery_sidecar")

    return errors


def verify_p1_step8_identity_projection_boundary_v1() -> list[str]:
    """Return error codes if phase 03 still enqueues identity audit replay jobs (P1 step 8)."""
    errors: list[str] = []
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    p03 = inspect.getsource(pr_mod.run_phase_03_identity_v1)
    if "finalize_identity_substrate_operator_audit" in p03:
        errors.append("phase03_still_calls_finalize_identity_substrate_operator_audit")
    if "identity_substrate_audit_replay_job_id" in p03:
        errors.append("phase03_still_exports_audit_replay_job_id")
    if "execute_org_link_replay_job" in p03:
        errors.append("phase03_still_calls_org_link_replay_job")
    if "run_identity_substrate_projection_for_pipeline_v1" not in p03:
        errors.append("phase03_missing_run_identity_substrate_projection_for_pipeline_v1")

    from vector.domains.cortex.identity import continuity_rebuild as id_mod

    if not callable(getattr(id_mod, "run_identity_substrate_projection_for_pipeline_v1", None)):
        errors.append("missing_run_identity_substrate_projection_for_pipeline_v1")
    if not callable(getattr(id_mod, "build_identity_substrate_projection_receipt_v1", None)):
        errors.append("missing_build_identity_substrate_projection_receipt_v1")
    return errors


def verify_p0_step7_determinism_repair_off_hot_path_v1() -> list[str]:
    """Return error codes if phase 02 still runs determinism repair inline (P0 step 7)."""
    errors: list[str] = []
    from vector.domains.cortex.execution import admin_commands as cmd_mod
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    p02 = inspect.getsource(pr_mod.run_phase_02_canonical_v1)
    if "repair_tenant_materialization_oracle_determinism_drift" in p02:
        errors.append("phase02_still_runs_inline_determinism_repair")
    if "determinism_repair" in p02:
        errors.append("phase02_still_exports_determinism_repair_in_output")

    if not callable(getattr(cmd_mod, "run_canonical_determinism_repair_v1", None)):
        errors.append("missing_run_canonical_determinism_repair_v1_admin_hook")
    rerun_src = inspect.getsource(cmd_mod.execution_rerun_v1)
    if "run_determinism_repair" not in rerun_src:
        errors.append("execution_rerun_missing_optional_determinism_repair")
    return errors


def verify_p0_step6_no_pass_fairness_on_lease_v1() -> list[str]:
    """Return error codes if execution lease still stores pass-fairness state (P0 step 6)."""
    errors: list[str] = []
    from vector.domains.cortex.execution import run_tenant_execution as exec_mod
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    exec_src = inspect.getsource(exec_mod.run_tenant_convergence_v1)
    for sym in (
        "_canonical_pass_index_from_lease",
        "_store_canonical_pass_index_on_lease",
        "_store_pass_fairness_on_lease",
        "parse_pass_cooldown_until",
        "parse_pass_topology_stall_counts",
    ):
        if sym in exec_src:
            errors.append(f"execution_worker_still_uses_pass_fairness:{sym}")

    if "_store_canonical_slice_outcome_on_lease" not in exec_src:
        errors.append("execution_worker_missing_canonical_slice_outcome_store")

    p02 = inspect.getsource(pr_mod.run_phase_02_canonical_v1)
    if "pass_index: int" in p02:
        errors.append("phase02_runner_still_accepts_pass_index_parameter")
    if "pass_cooldowns:" in p02 or "pass_stall_counts:" in p02:
        errors.append("phase02_runner_still_accepts_pass_fairness_parameters")
    return errors


def verify_p0_step5_canonical_single_drain_v1() -> list[str]:
    """Return error codes if phase 02 still uses dual drain / drain_stub (P0 step 5)."""
    errors: list[str] = []
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    p02 = inspect.getsource(pr_mod.run_phase_02_canonical_v1)
    if "drain_stub_materialize_backlog" in p02:
        errors.append("phase02_still_calls_drain_stub_materialize_backlog")
    if "slack_preface" in p02:
        errors.append("phase02_still_has_slack_preface_dual_drain")
    if p02.count("drain_forward_progress_backlog(") != 1:
        errors.append("phase02_must_call_drain_forward_progress_backlog_exactly_once")
    return errors


def verify_p0_step4_no_continuation_on_execution_hot_path_v1() -> list[str]:
    """Return error codes if execution hot path still writes pipeline_continuation (P0 step 4)."""
    errors: list[str] = []
    from vector.domains.cortex.execution import run_tenant_execution as exec_mod
    from vector.domains.cortex.synthesis import synthesis_pipeline as syn_mod
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    p06 = inspect.getsource(pr_mod.run_phase_06_tcre_v1)
    if "pipeline_continuation" in p06 or "mark_pipeline_waiting_on_tcre_v1" in p06:
        errors.append("phase06_runner_still_writes_pipeline_continuation")

    p08 = inspect.getsource(syn_mod.run_substrate_phase_08_synthesis_v1)
    if "mark_continuation_completed_v1" in p08 or "pipeline_continuation" in p08:
        errors.append("phase08_runner_still_writes_pipeline_continuation")

    exec_src = inspect.getsource(exec_mod.run_tenant_convergence_v1)
    if "pipeline_continuation" in exec_src or "mark_pipeline_waiting_on_tcre_v1" in exec_src:
        errors.append("execution_worker_still_writes_pipeline_continuation")
    if "mark_tenant_waiting_v1" not in exec_src:
        errors.append("execution_worker_missing_mark_tenant_waiting_on_tcre")

    if "assert_pipe085_chain_after_phase06_legal_v1" not in exec_src:
        errors.append("execution_worker_missing_pipe085_lease_assert_after_phase06")
    return errors


def verify_p0_step3_single_tcre_resume_path_v1() -> list[str]:
    """Return error codes if TCRE completion still uses continuation resume (P0 step 3)."""
    errors: list[str] = []
    from vector.domains.cortex.execution import tcre_resume as tcre_mod
    from vector.domains.cortex.substrate_pipeline import orchestrator as orch_mod

    tcre_src = inspect.getsource(tcre_mod.on_tcre_job_terminal_for_execution_v1)
    if "resume_pipeline_after_tcre_completion_v1" in tcre_src:
        errors.append("tcre_resume_still_calls_continuation_resume")
    if "resume_convergence_from_waiting_v1" not in tcre_src:
        errors.append("tcre_resume_missing_convergence_lease_resume")
    if "enqueue_tenant_convergence_v1" not in tcre_src:
        errors.append("tcre_resume_missing_convergence_enqueue")

    orch_src = inspect.getsource(orch_mod.on_tcre_job_completed_for_pipeline_v1)
    if "resume_pipeline_after_tcre_completion_v1" in orch_src:
        errors.append("on_tcre_pipeline_still_calls_continuation_resume")
    if "on_tcre_job_terminal_for_execution_v1" not in orch_src:
        errors.append("on_tcre_pipeline_missing_execution_terminal_resume")

    from vector.domains.cortex.substrate_pipeline import stalled_pipeline_recovery as rec_mod

    rec_src = inspect.getsource(rec_mod.recover_stalled_pipeline_v1)
    if "resume_pipeline_after_tcre_completion_v1" in rec_src:
        errors.append("stalled_recovery_still_calls_continuation_resume")
    if "on_tcre_job_terminal_for_execution_v1" not in rec_src:
        errors.append("stalled_recovery_missing_execution_terminal_resume")
    return errors


def verify_p0_step2_phase06_tcre_worker_boundary_v1() -> list[str]:
    """Return error codes if TCRE Celery worker still materializes retrieval (P0 step 2)."""
    import importlib.util

    errors: list[str] = []
    spec = importlib.util.find_spec("app.tasks.cortex_tcre_reconstruction_jobs")
    if spec is None or spec.origin is None:
        errors.append("missing_cortex_tcre_reconstruction_jobs_module")
        return errors
    from pathlib import Path

    src = Path(spec.origin).read_text(encoding="utf-8")
    if "materialize_retrieval_index_incremental_after_tcre_v1" in src:
        errors.append("tcre_worker_still_calls_incremental_retrieval_materialization")
    if "materialize_retrieval_index" in src:
        errors.append("tcre_worker_still_imports_retrieval_materialization")
    if "on_tcre_job_completed_for_pipeline_v1" not in src:
        errors.append("tcre_worker_missing_pipeline_resume_on_completion")
    return errors


def verify_p0_step1_phase07_retrieval_boundary_v1() -> list[str]:
    """Return error codes if phase 07 still runs synthesis activation (P0 step 1)."""
    from vector.domains.cortex.synthesis import synthesis_pipeline as syn_mod
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    errors: list[str] = []
    p07 = inspect.getsource(pr_mod.run_phase_07_retrieval_v1)
    if "run_synthesis_activation_after_phase07_v1" in p07:
        errors.append("phase07_still_calls_synthesis_activation")
    p08 = inspect.getsource(syn_mod.run_substrate_phase_08_synthesis_v1)
    if "evaluate_synthesis_activation_schedule_v1" not in p08:
        errors.append("phase08_missing_synthesis_activation_evaluation")
    from vector.domains.cortex.execution import run_tenant_execution as exec_mod

    exec_src = inspect.getsource(exec_mod.run_tenant_convergence_v1)
    if "synthesis_activation" in exec_src:
        errors.append("execution_worker_still_reads_synthesis_activation_from_phase07")
    return errors


def verify_m8_admin_execution_surface_v1() -> list[str]:
    """Return error codes if M8 consolidated admin execution routes are missing."""
    errors: list[str] = []
    try:
        from vector.api.http.routes import admin_cortex_execution as exec_routes
    except ImportError:
        errors.append("missing_admin_cortex_execution_routes_module")
        return errors

    src = inspect.getsource(exec_routes.register_cortex_execution_routes)
    for suffix in ("/state", "/restart", "/clear", "/rerun", "/transition-log"):
        if suffix not in src:
            errors.append(f"missing_execution_route:{suffix}")

    from vector.domains.cortex.execution import admin_commands as cmd_mod

    for sym in (
        "build_execution_inspect_v1",
        "restart_execution_from_phase_v1",
        "clear_derived_execution_outputs_v1",
        "execution_rerun_v1",
    ):
        if not callable(getattr(cmd_mod, sym, None)):
            errors.append(f"missing_admin_command:{sym}")

    import importlib

    admin_mod = importlib.import_module("vector.api.http.routes.admin")
    if "register_cortex_execution_routes" not in inspect.getsource(admin_mod.build_admin_router):
        errors.append("admin_router_missing_execution_registration")
    router_src = inspect.getsource(admin_mod.build_admin_router)
    if "materialize-backlog" not in router_src or "raise_admin_endpoint_gone" not in router_src:
        errors.append("materialize_backlog_missing_410_guard")
    return errors
