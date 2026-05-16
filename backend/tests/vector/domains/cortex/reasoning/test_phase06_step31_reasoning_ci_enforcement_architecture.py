"""P06-31 — Reasoning **G-P06-*** CI enforcement architecture (STAGE topology + bundles)."""

from __future__ import annotations

from vector.domains.cortex.reasoning.reasoning_ci_enforcement_architecture import (
    PHASE06_REASONING_CI_ENFORCEMENT_ARCHITECTURE_RUNTIME_SCHEMA_VERSION,
    REASONING_CI_ENFORCEMENT_ARCH_HARNESS_SPEC_REF_V1,
    REASONING_CI_ENFORCEMENT_ARCH_PHASE05_REF_V1,
    REASONING_GP06_CI_FULL_STATIC_STAGES_V1,
    REASONING_GP06_CI_INVARIANT_PARALLEL_STAGES_V1,
    REASONING_GP06_CI_PR_BLOCKING_STAGES_V1,
    list_reasoning_gp06_ci_stage_letters_ordered_v1,
    reasoning_gp06_ci_full_stage_row_map_v1,
    run_reasoning_gp06_ci_full_az_topology_with_meta_v1,
    run_reasoning_gp06_ci_full_wired_stages_with_meta_v1,
    run_reasoning_gp06_ci_pr_blocking_bundle_v1,
    verify_gp06_cia01_full_stage_row_partition_covers_doctrine_static,
    verify_gp06_cia02_pr_blocking_stages_match_constant_and_underlying_static,
    verify_gp06_cia03_severity_defaults_hard_fail_all_doctrine_static,
    verify_gp06_cia04_wired_runner_keys_equal_doctrine_static,
    verify_gp06_cia05_full_az_topology_including_empty_rows_passes_static,
    verify_gp06_cia06_close_gate_is_last_in_stage_z_static,
    verify_gp06_cia07_phase05_doc_anchor_present_static,
    verify_gp06_cia08_ci_invariant_literal_frozen_static,
)


def test_runtime_constants() -> None:
    assert PHASE06_REASONING_CI_ENFORCEMENT_ARCHITECTURE_RUNTIME_SCHEMA_VERSION >= 1
    assert "05-traversal" in REASONING_CI_ENFORCEMENT_ARCH_PHASE05_REF_V1
    hspec = REASONING_CI_ENFORCEMENT_ARCH_HARNESS_SPEC_REF_V1
    assert "reasoning-verification-harness-spec" in hspec
    assert "parallel" in REASONING_GP06_CI_INVARIANT_PARALLEL_STAGES_V1.lower()


def test_full_stage_row_map_shape() -> None:
    row = reasoning_gp06_ci_full_stage_row_map_v1()
    letters = list_reasoning_gp06_ci_stage_letters_ordered_v1()
    assert tuple(row.keys()) == letters
    nonempty = sum(1 for v in row.values() if v)
    assert nonempty == 6  # A,B,C,D,E,Z populated in v1
    assert row["F"] == ()


def test_all_cia_oracles_pass() -> None:
    assert verify_gp06_cia01_full_stage_row_partition_covers_doctrine_static()["passed"] is True
    cia02 = verify_gp06_cia02_pr_blocking_stages_match_constant_and_underlying_static()
    assert cia02["passed"] is True
    assert verify_gp06_cia03_severity_defaults_hard_fail_all_doctrine_static()["passed"] is True
    assert verify_gp06_cia04_wired_runner_keys_equal_doctrine_static()["passed"] is True
    assert verify_gp06_cia05_full_az_topology_including_empty_rows_passes_static()["passed"] is True
    assert verify_gp06_cia06_close_gate_is_last_in_stage_z_static()["passed"] is True
    assert verify_gp06_cia07_phase05_doc_anchor_present_static()["passed"] is True
    assert verify_gp06_cia08_ci_invariant_literal_frozen_static()["passed"] is True


def test_pr_blocking_bundle_metadata() -> None:
    out = run_reasoning_gp06_ci_pr_blocking_bundle_v1()
    assert out["passed"] is True
    assert out["reasoning_gp06_ci_pr_blocking_stages_v1"] == REASONING_GP06_CI_PR_BLOCKING_STAGES_V1
    assert out["reasoning_gp06_ci_pr_blocking_stages_v1"] == ("A", "B", "C", "D")


def test_full_wired_and_topology_meta_bundles_pass() -> None:
    w = run_reasoning_gp06_ci_full_wired_stages_with_meta_v1()
    assert w["passed"] is True
    assert w["reasoning_gp06_ci_full_static_stages_v1"] == REASONING_GP06_CI_FULL_STATIC_STAGES_V1
    assert w["reasoning_gp06_ci_full_static_stages_v1"] == ("A", "B", "C", "D", "E", "Z")
    assert "meta_results" in w
    t = run_reasoning_gp06_ci_full_az_topology_with_meta_v1()
    assert t["passed"] is True
    assert len(t["reasoning_gp06_ci_topology_stages_v1"]) == 26
