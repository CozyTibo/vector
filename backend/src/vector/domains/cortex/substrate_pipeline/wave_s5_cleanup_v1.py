"""Wave S5 — operator cleanup contract (delete theater, semantic-primary KPIs)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

WAVE_S5_CLEANUP_SCHEMA_VERSION: Final[int] = 1
WAVE_S5_STEP_21: Final[str] = "wave_s5_semantic_cleanup_delete"

DEPRECATED_OPERATOR_PRIMARY_METRICS_V1: Final[frozenset[str]] = frozenset(
    {
        "raw_minus_mat_admin_gap",
        "authoritative_link_rows_primary",
        "auth_edge_rows_primary",
        "candidate_rows_primary",
        "edge_count_primary",
        "phase_04_edge_count_receipt",
    }
)

DEPRECATED_OPERATOR_SCRIPTS_V1: Final[tuple[str, ...]] = (
    "prod_substrate_proof_queries.py",
    "continuity_proof_panel.py",
)


def is_semantic_primary_operator_kpi_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_wave_s5_semantic_primary_operator_kpi)
    except Exception:  # noqa: BLE001
        return True


def verify_legacy_coordinator_enqueue_deleted_v1() -> dict[str, Any]:
    from vector.domains.cortex.execution.scheduling import (
        verify_d5_legacy_coordinator_enqueue_paths_deleted_v1,
    )

    errors = list(verify_d5_legacy_coordinator_enqueue_paths_deleted_v1())
    return {
        "schema_version": WAVE_S5_CLEANUP_SCHEMA_VERSION,
        "coordinator_enqueue_deleted": not errors,
        "errors": errors,
        "authoritative_motion": "mark_dirty_and_enqueue_convergence_v1",
    }


def verify_s5_1_deletes_v1() -> dict[str, Any]:
    """S5.1 — duplicate Celery run_tenant task and serial fallback removed."""
    import inspect as _inspect

    from app import celery_app as celery_mod

    errors: list[str] = []
    conv_src = _inspect.getsource(__import__("app.tasks.cortex_convergence", fromlist=[""]))
    if "run_tenant_convergence_task" in conv_src:
        errors.append("celery_convergence_run_tenant_task_still_defined")
    if "vector.cortex.convergence.run_tenant" in conv_src and "@celery_app.task" in conv_src:
        if 'name="vector.cortex.convergence.run_tenant"' in conv_src or "name=_TASK_RUN" in conv_src:
            errors.append("celery_convergence_run_tenant_task_still_registered")

    from vector.domains.cortex.execution import run_tenant_execution as rte_mod

    rte_src = _inspect.getsource(rte_mod.run_tenant_convergence_v1)
    if "while phase in SUBSTRATE_PIPELINE_PHASE_ORDER" in rte_src:
        errors.append("serial_phase_loop_still_present")
    if "ExecutionSerialFallbackRemovedError" not in rte_src:
        errors.append("serial_fallback_fail_loud_missing")

    kpi_src = _inspect.getsource(
        __import__(
            "vector.domains.cortex.pipeline.pipeline_admin_operator_kpi",
            fromlist=["build_operator_primary_kpi_v1"],
        ).build_operator_primary_kpi_v1
    )
    if "OPERATOR_KPI_DEPRECATED_RAW_GAP_V1" in kpi_src:
        errors.append("legacy_auth_link_kpi_branch_still_present")
    if "semantic_primary_active" not in kpi_src or "hide_from_overview" not in kpi_src:
        errors.append("semantic_primary_kpi_not_wired")

    return {
        "schema_version": WAVE_S5_CLEANUP_SCHEMA_VERSION,
        "s5_1_ok": not errors,
        "errors": errors,
    }


def verify_unlock_wedge_scripts_not_imported_v1(*, repo_root: Path | None = None) -> dict[str, Any]:
    """S5.1 — production code must not import archived unlock wedge scripts."""
    root = repo_root or Path(__file__).resolve().parents[6]
    src_root = root / "backend" / "src"
    needle = "archive/unlock"
    violations: list[str] = []
    allowed_name = "continuity_cleanup_freeze.py"
    if src_root.is_dir():
        for path in src_root.rglob("*.py"):
            if path.name == allowed_name:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if needle in text:
                violations.append(str(path.relative_to(root)))
    return {
        "schema_version": WAVE_S5_CLEANUP_SCHEMA_VERSION,
        "import_ban_ok": not violations,
        "violations": violations,
    }


def snapshot_wave_s5_delete_contract_v1() -> dict[str, Any]:
    return {
        "schema_version": WAVE_S5_CLEANUP_SCHEMA_VERSION,
        "semantic_primary_operator_kpi": is_semantic_primary_operator_kpi_enabled_v1(),
        "deprecated_operator_scripts": list(DEPRECATED_OPERATOR_SCRIPTS_V1),
        "deprecated_primary_metrics": sorted(DEPRECATED_OPERATOR_PRIMARY_METRICS_V1),
        "coordinator": verify_legacy_coordinator_enqueue_deleted_v1(),
        "s5_1_deletes": verify_s5_1_deletes_v1(),
        "unlock_import_ban": verify_unlock_wedge_scripts_not_imported_v1(),
    }
