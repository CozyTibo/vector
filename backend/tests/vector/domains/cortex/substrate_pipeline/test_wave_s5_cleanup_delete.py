"""Wave S5 step 21 — delete theater (coordinator paths, deprecated operator metrics/scripts)."""

from __future__ import annotations

from vector.domains.cortex.substrate_pipeline.wave_s5_cleanup_v1 import (
    DEPRECATED_OPERATOR_PRIMARY_METRICS_V1,
    DEPRECATED_OPERATOR_SCRIPTS_V1,
    WAVE_S5_STEP_21,
    is_semantic_primary_operator_kpi_enabled_v1,
    snapshot_wave_s5_delete_contract_v1,
    verify_legacy_coordinator_enqueue_deleted_v1,
)


def test_legacy_coordinator_enqueue_paths_deleted() -> None:
    result = verify_legacy_coordinator_enqueue_deleted_v1()
    assert result["coordinator_enqueue_deleted"] is True
    assert result["errors"] == []


def test_wave_s5_delete_contract_snapshot() -> None:
    snap = snapshot_wave_s5_delete_contract_v1()
    assert snap["schema_version"] == 1
    assert snap["coordinator"]["coordinator_enqueue_deleted"] is True
    assert "raw_minus_mat_admin_gap" in DEPRECATED_OPERATOR_PRIMARY_METRICS_V1
    assert "authoritative_link_rows_primary" in DEPRECATED_OPERATOR_PRIMARY_METRICS_V1
    assert any("prod_substrate_proof_queries" in s for s in DEPRECATED_OPERATOR_SCRIPTS_V1)


def test_semantic_primary_operator_kpi_enabled_by_default() -> None:
    assert is_semantic_primary_operator_kpi_enabled_v1() is True


def test_wave_s5_s5_1_deletes_contract() -> None:
    from vector.domains.cortex.substrate_pipeline.wave_s5_cleanup_v1 import verify_s5_1_deletes_v1

    out = verify_s5_1_deletes_v1()
    assert out["s5_1_ok"] is True, out["errors"]


def test_wave_s5_step_constant() -> None:
    assert WAVE_S5_STEP_21 == "wave_s5_semantic_cleanup_delete"
