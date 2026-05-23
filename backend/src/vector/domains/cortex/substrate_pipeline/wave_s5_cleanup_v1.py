"""Wave S5 — operator cleanup contract (delete theater, semantic-primary KPIs)."""

from __future__ import annotations

from typing import Any, Final

WAVE_S5_CLEANUP_SCHEMA_VERSION: Final[int] = 1
WAVE_S5_STEP_21: Final[str] = "wave_s5_semantic_cleanup_delete"

DEPRECATED_OPERATOR_PRIMARY_METRICS_V1: Final[frozenset[str]] = frozenset(
    {
        "raw_minus_mat_admin_gap",
        "authoritative_link_rows_primary",
        "auth_edge_rows_primary",
        "candidate_rows_primary",
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


def snapshot_wave_s5_delete_contract_v1() -> dict[str, Any]:
    return {
        "schema_version": WAVE_S5_CLEANUP_SCHEMA_VERSION,
        "semantic_primary_operator_kpi": is_semantic_primary_operator_kpi_enabled_v1(),
        "deprecated_operator_scripts": list(DEPRECATED_OPERATOR_SCRIPTS_V1),
        "deprecated_primary_metrics": sorted(DEPRECATED_OPERATOR_PRIMARY_METRICS_V1),
        "coordinator": verify_legacy_coordinator_enqueue_deleted_v1(),
    }
