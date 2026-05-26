"""Tenant execution scheduling helpers (authoritative beat + ingest path)."""

from __future__ import annotations

import inspect
import os
from pathlib import Path
from typing import Final

from vector.settings import Settings

CELERY_CONVERGENCE_SWEEP_BEAT_KEY_V1: Final[str] = "cortex-convergence-sweep"
CELERY_CONVERGENCE_SWEEP_TASK_NAME_V1: Final[str] = "vector.cortex.convergence.sweep"

# Removed S5.1 — use vector.cortex.execution.run_slice only.
CELERY_CONVERGENCE_RUN_TASK_REMOVED_V1: Final[str] = "vector.cortex.convergence.run_tenant"
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
    if "mark_dirty_and_enqueue_convergence_v1" not in src:
        errors.append("schedule_substrate_pipeline_missing_convergence_enqueue")
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
    if "run_traversal_slice_for_pipeline_v1" not in p05:
        errors.append("phase05_missing_run_traversal_slice_for_pipeline_v1")
    if "run_octs_walk_schedule_pass_v1" in p05:
        errors.append("phase05_still_calls_octs_walk_schedule_pass")
    if "run_substrate_traversal_materialization_v1" in p05:
        errors.append("phase05_still_calls_substrate_traversal_materialization_directly")
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


D5_FORBIDDEN_CELERY_MODULES_V1: Final[tuple[str, ...]] = (
    "app.tasks.cortex_substrate_pipeline",
    "vector.domains.cortex.substrate_pipeline.coordinator",
    "vector.infrastructure.cortex_substrate_pipeline_schedule",
)

D5_FORBIDDEN_COORDINATOR_ENQUEUE_TOKENS_V1: Final[tuple[str, ...]] = (
    "run_cortex_substrate_pipeline_coordinator_task",
    "run_cortex_substrate_pipeline_phase_task",
)

D5_SOURCE_SCAN_SKIP_FILES_V1: Final[tuple[str, ...]] = (
    "execution/scheduling.py",
    "operational_runtime/substrate_runtime_economics.py",
)


def _scan_cortex_package_for_coordinator_enqueue_tokens_v1() -> list[str]:
    """D5: no live coordinator / per-phase Celery enqueue symbols under domains/cortex."""
    errors: list[str] = []
    cortex_root = Path(__file__).resolve().parent.parent
    for path in sorted(cortex_root.rglob("*.py")):
        rel = path.relative_to(cortex_root).as_posix()
        if rel.startswith("tests/") or "/tests/" in rel:
            continue
        if any(rel.endswith(skip) for skip in D5_SOURCE_SCAN_SKIP_FILES_V1):
            continue
        text = path.read_text(encoding="utf-8")
        for token in D5_FORBIDDEN_COORDINATOR_ENQUEUE_TOKENS_V1:
            if token in text:
                errors.append(f"forbidden_coordinator_enqueue_token:{token}:{rel}")
    return errors


def verify_d5_legacy_coordinator_enqueue_paths_deleted_v1() -> list[str]:
    """D5: legacy substrate coordinator + per-phase Celery enqueue paths must be absent."""
    import importlib.util

    errors: list[str] = []
    errors.extend(verify_schedule_substrate_pipeline_uses_convergence_v1())
    errors.extend(verify_no_legacy_phase_chain_v1())
    errors.extend(verify_m9_dead_celery_modules_absent_v1())
    errors.extend(_scan_cortex_package_for_coordinator_enqueue_tokens_v1())

    for mod in D5_FORBIDDEN_CELERY_MODULES_V1:
        if importlib.util.find_spec(mod) is not None:
            errors.append(f"d5_forbidden_module_still_present:{mod}")

    from vector.domains.cortex.substrate_pipeline import orchestrator as orch

    if hasattr(orch, "chain_after_phase_v1"):
        errors.append("chain_after_phase_v1_still_exported")

    from app.celery_app import celery_app

    if "app.tasks.cortex_substrate_pipeline" in str(celery_app.conf.imports or ()):
        errors.append("celery_imports_still_include_cortex_substrate_pipeline")

    return errors


def verify_d3_graph_promotion_on_convergence_worker_v1() -> list[str]:
    """Wave 1: promotion only in repair slice; no pre-slice convergence hook."""
    errors: list[str] = []
    errors.extend(verify_m9_dead_celery_modules_absent_v1())
    errors.extend(verify_convergence_sweep_in_celery_beat_v1())
    from vector.domains.cortex.execution import run_tenant_execution as rte_mod

    rte_src = inspect.getsource(rte_mod.run_tenant_convergence_v1)
    if "schedule_graph_density_promotion_on_convergence_worker_v1" in rte_src:
        errors.append("run_tenant_convergence_still_has_pre_slice_promotion_hook")
    from vector.domains.cortex.execution import dual_lane_worker as dl_mod

    dl_src = inspect.getsource(dl_mod.run_dual_lane_convergence_v1)
    if "schedule_graph_density_promotion_on_convergence_worker_v1" in dl_src:
        errors.append("dual_lane_convergence_still_has_pre_slice_promotion_hook")
    from vector.domains.cortex.identity import identity_substrate_repair_v1 as repair_mod

    repair_src = inspect.getsource(repair_mod.run_identity_substrate_repair_slice_v1)
    if "schedule_graph_density_pass_v1" not in repair_src:
        errors.append("repair_slice_missing_schedule_graph_density_pass_v1")
    from vector.domains.cortex.operational_runtime import graph_density_promotion as promo_mod

    promo_src = inspect.getsource(promo_mod.schedule_graph_density_pass_v1)
    if "inline_execution_slice" not in promo_src:
        errors.append("schedule_graph_density_pass_missing_inline_path")
    if hasattr(promo_mod, "schedule_graph_density_promotion_on_convergence_worker_v1"):
        errors.append("convergence_worker_promotion_hook_must_be_deleted")
    return errors


def verify_wave2_operator_paths_v1() -> list[str]:
    """Wave 2: rebuild_identities is reset+dirty; collapsed replay kinds blocked on primary API."""
    errors: list[str] = []
    from vector.domains.cortex.pipeline import operator_admin_actions as oa_mod

    oa_src = inspect.getsource(oa_mod.execute_operator_action_v1)
    if "operator_rebuild_identities_v1" not in oa_src:
        errors.append("operator_actions_missing_operator_rebuild_identities_v1")
    if "enqueue_rebuild_identities_from_anchors_v1" in oa_src:
        errors.append("operator_actions_still_calls_enqueue_rebuild_identities")

    from vector.domains.cortex.identity import continuity_rebuild as cr_mod

    enq = inspect.getsource(cr_mod.enqueue_rebuild_identities_from_anchors_v1)
    if "operator_rebuild_identities_v1" not in enq:
        errors.append("enqueue_rebuild_identities_not_collapsed_to_operator_path")

    from vector.domains.cortex.identity import identity_substrate_operator_v1 as op_mod

    if not callable(getattr(op_mod, "operator_rebuild_identities_v1", None)):
        errors.append("missing_operator_rebuild_identities_v1")

    from vector.api.http.routes import admin as admin_mod

    admin_src = inspect.getsource(admin_mod.build_admin_router)
    if "register_cortex_debug_routes" not in admin_src:
        errors.append("admin_router_missing_cortex_debug_routes")
    if "assert_primary_replay_job_kind_allowed_v1" not in admin_src:
        errors.append("primary_replay_run_missing_wave2_job_kind_guard")

    from vector.domains.cortex.identity import control_plane as cp_mod

    guide = str(cp_mod.OPERATIONAL_REPLAY_CANONICAL_GUIDE.get("operator_rule") or "")
    if "identity_continuity_rebuild" in guide and "Prefer" in guide:
        errors.append("control_plane_still_prefers_identity_continuity_rebuild")

    from vector.domains.cortex.identity import debug_full_substrate_refresh_v1 as dbg_mod

    if not callable(getattr(dbg_mod, "run_debug_full_substrate_refresh_v1", None)):
        errors.append("missing_run_debug_full_substrate_refresh_v1")

    return errors


def verify_phase03_identity_projection_boundary_v1() -> list[str]:
    """Return error codes if phase 03 still enqueues identity audit replay jobs ."""
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
    if "resolve_phase_03_outcome_v1" not in p03:
        errors.append("phase03_missing_resolve_phase_03_outcome_v1")
    proj = inspect.getsource(id_mod.run_identity_substrate_projection_for_pipeline_v1)
    if "trigger_identity_promotion_after_substrate_v1" in proj:
        errors.append("phase03_still_calls_event_trigger_promotion")
    if "schedule_graph_density_promotion_after_identity_substrate_v1" in proj:
        errors.append("phase03_still_calls_duplicate_promotion_helper")
    from vector.domains.cortex.execution import execution_event_triggers as et_mod

    et_src = inspect.getsource(et_mod.trigger_identity_promotion_after_substrate_v1)
    if "schedule_graph_density_promotion_after_identity_substrate_v1" in et_src:
        errors.append("event_trigger_still_schedules_promotion")
    from vector.domains.cortex.substrate_pipeline import phase_runner_receipt as prr_mod

    if "_persist_phase_run_for_receipt_outcome_v1" not in inspect.getsource(
        prr_mod.complete_phase_with_receipt_v1
    ):
        errors.append("phase_receipt_missing_status_alignment_helper")
    return errors


def verify_phase04_graph_projection_export_boundary_v1() -> list[str]:
    """Return error codes if phase 04 still uses replay jobs or verification slice ."""
    errors: list[str] = []
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    p04 = inspect.getsource(pr_mod.run_phase_04_graph_v1)
    if "execute_org_link_replay_job" in p04:
        errors.append("phase04_still_calls_org_link_replay_job")
    if "graph_projection_export_job_id" in p04:
        errors.append("phase04_still_exports_graph_projection_export_job_id")
    if "build_org_graph_traversal_verification_slice_v1" in p04:
        errors.append("phase04_still_builds_org_graph_traversal_verification_slice")
    if "org_graph_traversal_verification_slice" in p04:
        errors.append("phase04_still_exports_org_graph_traversal_verification_slice")
    if "run_graph_projection_export_for_pipeline_v1" not in p04:
        errors.append("phase04_missing_run_graph_projection_export_for_pipeline_v1")

    from vector.domains.cortex.identity import projection_export as pe_mod

    if not callable(getattr(pe_mod, "run_graph_projection_export_for_pipeline_v1", None)):
        errors.append("missing_run_graph_projection_export_for_pipeline_v1")
    return errors


def verify_phase05_traversal_slice_boundary_v1() -> list[str]:
    """Return error codes if phase 05 still splits materialization + schedule pass ."""
    errors: list[str] = []
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    p05 = inspect.getsource(pr_mod.run_phase_05_traversal_v1)
    if "run_traversal_slice_for_pipeline_v1" not in p05:
        errors.append("phase05_missing_run_traversal_slice_for_pipeline_v1")
    if "run_octs_walk_schedule_pass_v1" in p05:
        errors.append("phase05_still_calls_octs_walk_schedule_pass")
    if "run_substrate_traversal_materialization_v1" in p05:
        errors.append("phase05_still_calls_substrate_traversal_materialization_directly")
    if "octs_walk_schedule" in p05:
        errors.append("phase05_still_exports_octs_walk_schedule")
    if "traversal_explainability_panel" in p05:
        errors.append("phase05_still_exports_traversal_explainability_panel")
    if "mark_pipeline_waiting_on_traversal_v1" in p05:
        errors.append("phase05_still_writes_traversal_continuation_wait")

    from vector.domains.cortex.substrate_pipeline import substrate_traversal_execution as ste_mod

    if not callable(getattr(ste_mod, "run_traversal_slice_for_pipeline_v1", None)):
        errors.append("missing_run_traversal_slice_for_pipeline_v1")
    pick_src = inspect.getsource(ste_mod._pick_start_node_ids_v1)
    if ".sort()" not in pick_src:
        errors.append("pick_start_node_ids_must_sort_deterministically")
    slice_src = inspect.getsource(ste_mod.run_traversal_slice_for_pipeline_v1)
    if "_pick_execution_anchor_start_node_ids_v1" not in slice_src:
        errors.append("traversal_slice_must_pick_execution_anchor_starts")
    if "execution_anchor_count" not in slice_src:
        errors.append("traversal_slice_must_emit_execution_anchor_count")
    return errors


def verify_ingestion_sync_split_boundary_v1() -> list[str]:
    """Return error codes if sync_executor is still monolithic or modes not collapsed ."""
    errors: list[str] = []
    import importlib.util
    from pathlib import Path

    ingest_root = Path(__file__).resolve().parent.parent / "ingestion"
    shim = ingest_root / "sync_executor.py"
    if shim.is_file() and shim.stat().st_size > 4000:
        errors.append("sync_executor_still_monolithic")

    for connector in ("github", "linear", "slack", "notion", "calls"):
        mod_path = ingest_root / "connectors" / connector / "sync.py"
        if not mod_path.is_file():
            errors.append(f"missing_connector_sync_module:{connector}")

    router_path = ingest_root / "sync_router.py"
    if not router_path.is_file():
        errors.append("missing_sync_router")
    else:
        router_src = router_path.read_text(encoding="utf-8")
        if "run_github_connector_sync" not in router_src:
            errors.append("sync_router_missing_github_dispatch")
        if "run_calls_connector_sync" not in router_src:
            errors.append("sync_router_missing_calls_dispatch")

    from vector.domains.cortex.ingestion import sync_context as sc_mod

    allowed: frozenset[str] = getattr(sc_mod, "_ALLOWED_SYNC_MODES", frozenset())
    if allowed != frozenset({"live", "replay"}):
        errors.append("sync_context_modes_not_collapsed_to_live_replay")

    ctx_src = inspect.getsource(sc_mod.IngestionSyncContext)
    if "checkpoint_sync_mode" not in ctx_src:
        errors.append("sync_context_missing_checkpoint_sync_mode")
    if 'sync_mode="incremental"' in ctx_src or 'sync_mode="backfill"' in ctx_src:
        errors.append("sync_context_still_uses_legacy_mode_strings")

    celery_path = Path(__file__).resolve().parents[4] / "app" / "tasks" / "cortex_ingestion_sync.py"
    if not celery_path.is_file():
        celery_path = Path(__file__).resolve().parents[5] / "app" / "tasks" / "cortex_ingestion_sync.py"
    if celery_path.is_file():
        celery_src = celery_path.read_text(encoding="utf-8")
        for forbidden in (
            "run_phase_",
            "substrate_pipeline",
            "mark_pipeline_waiting",
            "execute_org_link_replay_job",
        ):
            if forbidden in celery_src:
                errors.append(f"ingestion_celery_imports_substrate:{forbidden}")

    if importlib.util.find_spec("vector.domains.cortex.ingestion.sync_shared") is None:
        errors.append("missing_sync_shared_module")

    return errors


EXECUTION_HOT_PATH_MODULE_NAMES_V1: Final[tuple[str, ...]] = (
    "vector.domains.cortex.execution.run_tenant_execution",
    "vector.domains.cortex.substrate_pipeline.phase_runners",
    "vector.domains.cortex.synthesis.synthesis_pipeline",
)

EXECUTION_HOT_PATH_FORBIDDEN_IMPORT_MARKERS_V1: Final[tuple[str, ...]] = (
    "operational_runtime",
    "verify_gp085",
    "cesp_certification",
)

EXECUTION_HOT_PATH_ALLOWED_OPERATIONAL_RUNTIME_IMPORTS_V1: Final[tuple[str, ...]] = (
    "vector.domains.cortex.operational_runtime.graph_density_promotion",
    "vector.domains.cortex.operational_runtime.execution_island_registry",
)


def _hot_path_operational_runtime_import_violations_v1(src: str) -> bool:
    for line in src.splitlines():
        if "operational_runtime" not in line or "import" not in line:
            continue
        if any(allowed in line for allowed in EXECUTION_HOT_PATH_ALLOWED_OPERATIONAL_RUNTIME_IMPORTS_V1):
            continue
        return True
    return False


def verify_execution_hot_path_no_cesp_imports_boundary_v1() -> list[str]:
    """Return error codes if execution/phase bodies import CESP doctrine ."""
    import importlib

    errors: list[str] = []
    for mod_name in EXECUTION_HOT_PATH_MODULE_NAMES_V1:
        mod = importlib.import_module(mod_name)
        src = inspect.getsource(mod)
        for marker in EXECUTION_HOT_PATH_FORBIDDEN_IMPORT_MARKERS_V1:
            if marker == "operational_runtime":
                if _hot_path_operational_runtime_import_violations_v1(src):
                    errors.append(f"{mod_name}_imports_{marker}")
                continue
            if marker in src:
                errors.append(f"{mod_name}_imports_{marker}")

    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    p06 = inspect.getsource(pr_mod.run_phase_06_tcre_v1)
    if "execution.phase06_contract" not in p06:
        errors.append("phase06_missing_execution_phase06_contract_import")
    if "enforce_phase06_progression_law_v1" not in p06:
        errors.append("phase06_missing_progression_enforcement")

    from vector.domains.cortex.synthesis import synthesis_pipeline as syn_mod

    p08 = inspect.getsource(syn_mod.run_substrate_phase_08_synthesis_v1)
    if "phase08_activation_gate" not in p08:
        errors.append("phase08_missing_phase08_activation_gate_import")
    if "evaluate_synthesis_activation_schedule_v1" not in p08:
        errors.append("phase08_missing_activation_evaluation")

    exec_mod = importlib.import_module("vector.domains.cortex.execution.run_tenant_execution")
    exec_src = inspect.getsource(exec_mod)
    if "execution.phase06_contract" not in exec_src:
        errors.append("run_tenant_execution_missing_phase06_contract_import")

    return errors


def verify_canonical_no_inline_determinism_repair_boundary_v1() -> list[str]:
    """Return error codes if phase 02 still runs determinism repair inline ."""
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


def verify_execution_lease_no_pass_fairness_boundary_v1() -> list[str]:
    """Return error codes if execution lease still stores pass-fairness state ."""
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

    from vector.domains.cortex.execution import dual_lane_worker as dl_mod

    dl_src = inspect.getsource(dl_mod)
    if "store_last_phase_receipt_on_lease_v1" not in dl_src:
        errors.append("dual_lane_worker_missing_phase_receipt_store")

    p02 = inspect.getsource(pr_mod.run_phase_02_canonical_v1)
    if "pass_index: int" in p02:
        errors.append("phase02_runner_still_accepts_pass_index_parameter")
    if "pass_cooldowns:" in p02 or "pass_stall_counts:" in p02:
        errors.append("phase02_runner_still_accepts_pass_fairness_parameters")
    return errors


def verify_canonical_deterministic_selection_v1() -> list[str]:
    """Return error codes if canonical drain still uses adaptive pass fairness."""
    errors: list[str] = []
    from vector.domains.cortex.canonical.forward_progress import pass_fairness as pf
    from vector.domains.cortex.canonical.forward_progress import drain_runtime as dr
    from vector.domains.cortex.canonical.forward_progress import candidate_selection as cs

    pf_src = inspect.getsource(pf.resolve_fair_pass_cursor)
    if "pass_is_on_cooldown" in pf_src:
        errors.append("resolve_fair_pass_cursor_still_skips_cooldown_passes")
    if "candidates.sort" in pf_src:
        errors.append("resolve_fair_pass_cursor_still_deprioritizes_stall_counts")

    cs_mod_src = inspect.getsource(cs)
    if "resolve_fair_pass_cursor" in inspect.getsource(cs.list_forward_progress_candidate_ids):
        errors.append("candidate_selection_still_uses_pass_rotation")
    if "source_identity_key" not in cs_mod_src:
        errors.append("candidate_selection_missing_source_identity_key_order")
    if "deterministic_fifo_v1" not in cs_mod_src:
        errors.append("candidate_selection_missing_deterministic_fifo_mode")

    drain_src = inspect.getsource(dr.drain_forward_progress_backlog)
    if "record_pass_topology_stall" in drain_src:
        errors.append("drain_still_records_pass_topology_stall")
    if "serialize_pass_cooldown_until" in drain_src:
        errors.append("drain_still_exports_pass_cooldown_state")
    if "canonical_receipt_hash" not in drain_src:
        errors.append("drain_missing_canonical_receipt_hash")
    return errors


def verify_unified_convergence_dispatch_v1() -> list[str]:
    """Return error codes if post-ingest and pipeline schedule diverge."""
    errors: list[str] = []
    from vector.domains.cortex.execution import convergence_dispatch as cd
    from vector.domains.cortex.ingestion import post_ingestion_refresh_dispatch as pid
    from vector.domains.cortex.substrate_pipeline import orchestrator as orch

    if not hasattr(cd, "mark_dirty_and_enqueue_convergence_v1"):
        errors.append("missing_mark_dirty_and_enqueue_convergence_v1")
    pid_src = inspect.getsource(pid.schedule_post_ingestion_substrate_refresh)
    if "mark_dirty_and_enqueue_convergence_v1" not in pid_src and (
        "trigger_post_ingestion_execution_v1" not in pid_src
    ):
        errors.append("post_ingestion_dispatch_not_unified")
    orch_src = inspect.getsource(orch.schedule_substrate_pipeline_v1)
    if "mark_dirty_and_enqueue_convergence_v1" not in orch_src:
        errors.append("schedule_substrate_pipeline_not_unified")
    return errors


def verify_pipeline_run_execution_mirror_v1() -> list[str]:
    """Return error codes if pipeline runs are not marked execution mirrors."""
    errors: list[str] = []
    from vector.domains.cortex.substrate_pipeline import repository as repo

    src = inspect.getsource(repo.create_pipeline_run_v1)
    if "execution_mirror_v1" not in src:
        errors.append("pipeline_run_missing_execution_mirror_flag")
    if "authoritative_surface" not in src:
        errors.append("pipeline_run_missing_authoritative_surface_marker")
    repo_src = inspect.getsource(repo.complete_phase_v1)
    if "_require_substrate_phase_receipt_in_output_v1" not in repo_src:
        errors.append("complete_phase_missing_receipt_requirement")
    return errors


def verify_topology_blocked_not_phase_waiting_v1() -> list[str]:
    """Return error codes if phase 02 topology defer still uses phase WAITING status."""
    errors: list[str] = []
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod

    p02 = inspect.getsource(pr_mod.run_phase_02_canonical_v1)
    if "wait_phase_with_receipt_v1" in p02:
        errors.append("phase02_still_uses_wait_phase_for_topology")
    if "PHASE_OUTCOME_BLOCKED" not in p02:
        errors.append("phase02_topology_missing_blocked_outcome")
    return errors


def verify_pipeline_continuation_writes_frozen_v1() -> list[str]:
    """Return error codes if continuation writes lack a runtime freeze guard."""
    errors: list[str] = []
    from vector.domains.cortex.substrate_pipeline import pipeline_continuation as cont

    if not hasattr(cont, "PipelineContinuationWriteFrozenError"):
        errors.append("missing_continuation_write_frozen_error")
    src = inspect.getsource(cont.mark_pipeline_waiting_on_tcre_v1)
    if "_assert_continuation_write_allowed_v1" not in src:
        errors.append("continuation_tcre_write_missing_freeze_guard")
    return errors


def verify_canonical_single_drain_boundary_v1() -> list[str]:
    """Return error codes if phase 02 still uses dual drain / drain_stub."""
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


def verify_execution_hot_path_no_continuation_boundary_v1() -> list[str]:
    """Return error codes if execution hot path still writes pipeline_continuation."""
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


def verify_single_tcre_execution_resume_boundary_v1() -> list[str]:
    """Return error codes if TCRE completion still uses continuation resume."""
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

    rec_src = inspect.getsource(rec_mod._recover_stalled_pipeline_impl_v1)
    if "resume_pipeline_after_tcre_completion_v1" in rec_src:
        errors.append("stalled_recovery_still_calls_continuation_resume")
    if "on_tcre_job_terminal_for_execution_v1" not in rec_src:
        errors.append("stalled_recovery_missing_execution_terminal_resume")
    return errors


def verify_tcre_worker_no_retrieval_materialization_boundary_v1() -> list[str]:
    """Return error codes if TCRE Celery worker still materializes retrieval."""
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


def verify_phase07_retrieval_only_boundary_v1() -> list[str]:
    """Return error codes if phase 07 still runs synthesis activation."""
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


def verify_execution_truth_unification_v1() -> list[str]:
    """Return error codes if operator status still treats continuation as default truth."""
    errors: list[str] = []
    import inspect as _inspect

    from vector.domains.cortex.execution import progression_status as ps

    sig = _inspect.signature(ps.build_substrate_progression_status_v1)
    if "include_legacy_continuation" not in sig.parameters:
        errors.append("progression_status_missing_include_legacy_continuation_flag")
    src = _inspect.getsource(ps.build_substrate_progression_status_v1)
    if "authoritative" not in src:
        errors.append("progression_status_lease_not_marked_authoritative")
    if "last_phase_receipt_hash" not in src:
        errors.append("progression_status_missing_last_phase_receipt_on_lease")
    return errors


def verify_execution_blocked_semantics_v1() -> list[str]:
    """Return error codes if execution worker lacks receipt-driven stop semantics."""
    errors: list[str] = []
    from vector.domains.cortex.execution import run_tenant_execution as exec_mod

    src = inspect.getsource(exec_mod.run_tenant_convergence_v1)
    for sym in (
        "store_last_phase_receipt_on_lease_v1",
        "WORKER_OUTCOME_WAITING_TCRE",
        "WORKER_OUTCOME_BLOCKED_RETRIEVAL",
        "worker_outcome_label_for_phase02_continue_v1",
    ):
        if sym not in src:
            errors.append(f"execution_worker_missing_{sym}")
    from vector.domains.cortex.substrate_pipeline import substrate_phase_receipt as spr

    if not hasattr(spr, "PHASE_OUTCOME_BLOCKED"):
        errors.append("missing_phase_outcome_blocked_constant")
    return errors


def verify_substrate_phase_receipt_contract_v1() -> list[str]:
    """Return error codes if phase runners omit universal substrate phase receipts."""
    errors: list[str] = []
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod
    from vector.domains.cortex.synthesis import synthesis_pipeline as syn_mod

    for name, src in (
        ("run_phase_02_canonical_v1", inspect.getsource(pr_mod.run_phase_02_canonical_v1)),
        ("run_phase_03_identity_v1", inspect.getsource(pr_mod.run_phase_03_identity_v1)),
        ("run_phase_04_graph_v1", inspect.getsource(pr_mod.run_phase_04_graph_v1)),
        ("run_phase_05_traversal_v1", inspect.getsource(pr_mod.run_phase_05_traversal_v1)),
        ("run_phase_06_tcre_v1", inspect.getsource(pr_mod.run_phase_06_tcre_v1)),
        ("run_phase_07_retrieval_v1", inspect.getsource(pr_mod.run_phase_07_retrieval_v1)),
        (
            "run_substrate_phase_08_synthesis_v1",
            inspect.getsource(syn_mod.run_substrate_phase_08_synthesis_v1),
        ),
    ):
        has_complete = (
            "complete_phase_with_receipt_v1" in src
            or "complete_async_phase_with_receipt_v1" in src
        )
        has_finish = has_complete or "skip_phase_with_receipt_v1" in src
        if not has_finish:
            errors.append(f"{name}_missing_receipt_helper")
        if "fail_phase_with_receipt_v1" not in src:
            if "try:" in src and name not in ("run_phase_03_identity_v1", "run_phase_02_canonical_v1"):
                errors.append(f"{name}_missing_fail_receipt_helper")

    try:
        from vector.domains.cortex.substrate_pipeline import substrate_phase_receipt as spr
    except ImportError:
        errors.append("missing_substrate_phase_receipt_module")
        return errors

    if not hasattr(spr, "build_substrate_phase_receipt_v1"):
        errors.append("missing_build_substrate_phase_receipt_v1")
    if not hasattr(spr, "PHASE_OUTCOME_COMPLETED"):
        errors.append("missing_phase_outcome_constants")
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

    from vector.domains.cortex.execution.admin_bypass_guard import (
        verify_no_admin_bypass_routes_registered_v1,
    )

    errors.extend(verify_no_admin_bypass_routes_registered_v1())
    return errors


def verify_legacy_runtime_burial_v1() -> list[str]:
    """Return error codes if dead post-ingest substrate refresh module still exists."""
    from pathlib import Path

    errors: list[str] = []
    legacy = (
        Path(__file__).resolve().parent.parent
        / "ingestion"
        / "post_ingestion_substrate_refresh.py"
    )
    if legacy.is_file():
        errors.append("post_ingestion_substrate_refresh_module_still_present")
    return errors


def verify_true_p0_substrate_signoff_v1() -> list[str]:
    """Aggregate TRUE P0 sign-off boundary verifiers (receipts, blocked, canonical, truth, burial)."""
    errors: list[str] = []
    errors.extend(verify_substrate_phase_receipt_contract_v1())
    errors.extend(verify_execution_blocked_semantics_v1())
    errors.extend(verify_canonical_deterministic_selection_v1())
    errors.extend(verify_unified_convergence_dispatch_v1())
    errors.extend(verify_pipeline_run_execution_mirror_v1())
    errors.extend(verify_topology_blocked_not_phase_waiting_v1())
    errors.extend(verify_pipeline_continuation_writes_frozen_v1())
    errors.extend(verify_execution_truth_unification_v1())
    errors.extend(verify_legacy_runtime_burial_v1())
    errors.extend(verify_execution_hot_path_no_cesp_imports_boundary_v1())
    errors.extend(verify_execution_hot_path_no_continuation_boundary_v1())
    errors.extend(verify_canonical_single_drain_boundary_v1())
    return errors
