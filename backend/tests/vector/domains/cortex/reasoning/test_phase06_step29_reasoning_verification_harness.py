"""P06-29 — G-P06-* verification harness (catalog + wired runners)."""

from __future__ import annotations

from vector.domains.cortex.reasoning.reasoning_verification_harness import (
    OCTS_CERT_PACK_REQUIRED_ROOT_FILES_V1,
    PHASE06_REASONING_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION,
    REASONING_GP06_CORRUPTION_BUNDLES_V1,
    REASONING_GP06_DOCTRINE_GATE_IDS_V1,
    REASONING_VERIFICATION_HARNESS_CATALOG_VERSION_V1,
    REASONING_VERIFICATION_HARNESS_SPEC_REF_V1,
    TCRE_CERT_PACK_FORMAT_LITERAL_V1,
    TCRE_CERT_PACK_MANIFEST_FORMAT_KEY_V1,
    default_severity_for_reasoning_gate_v1,
    list_reasoning_gp06_doctrine_gate_ids_v1,
    list_reasoning_gp06_wired_verification_runners_v1,
    reasoning_gp06_gate_stage_v1,
    run_reasoning_gp06_pr_blocking_static_stages_v1,
    run_reasoning_gp06_wired_verification_stages_v1,
    verify_gp06_close01_tcre_cert_pack_shape_reference_static,
    verify_gp06_rvh01_harness_catalog_covers_spec_gate_table_static,
    verify_gp06_rvh02_pr_blocking_bundle_passes_static,
    verify_gp06_rvh03_full_stage_az_includes_close_static,
    verify_reasoning_gp06_corruption_bundles_subset_static,
    verify_reasoning_gp06_gate_catalog_unique_ids_static,
    verify_reasoning_gp06_wired_runner_gate_ids_match_static,
)


def test_runtime_constants() -> None:
    assert PHASE06_REASONING_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION >= 1
    assert REASONING_VERIFICATION_HARNESS_CATALOG_VERSION_V1 >= 1
    assert "reasoning-verification-harness-spec" in REASONING_VERIFICATION_HARNESS_SPEC_REF_V1


def test_doctrine_gate_ids_sorted_unique() -> None:
    assert verify_reasoning_gp06_gate_catalog_unique_ids_static()["passed"] is True
    assert list_reasoning_gp06_doctrine_gate_ids_v1() == REASONING_GP06_DOCTRINE_GATE_IDS_V1


def test_corruption_bundles_subset() -> None:
    assert verify_reasoning_gp06_corruption_bundles_subset_static()["passed"] is True
    assert "replay_equivalence_surface" in REASONING_GP06_CORRUPTION_BUNDLES_V1


def test_wired_runner_ids_match_catalog_keys() -> None:
    assert verify_reasoning_gp06_wired_runner_gate_ids_match_static()["passed"] is True
    runners = list_reasoning_gp06_wired_verification_runners_v1()
    assert set(runners.keys()) == set(REASONING_GP06_DOCTRINE_GATE_IDS_V1)


def test_gate_stages_and_severity() -> None:
    assert reasoning_gp06_gate_stage_v1("G-P06-ANTI-01") == "A"
    assert reasoning_gp06_gate_stage_v1("G-P06-CLOSE-01") == "Z"
    assert reasoning_gp06_gate_stage_v1("unknown") is None
    assert default_severity_for_reasoning_gate_v1("G-P06-REPLAY-01") == "hard_fail"


def test_pr_blocking_and_full_az_pass() -> None:
    assert verify_gp06_rvh01_harness_catalog_covers_spec_gate_table_static()["passed"] is True
    assert verify_gp06_rvh02_pr_blocking_bundle_passes_static()["passed"] is True
    assert verify_gp06_rvh03_full_stage_az_includes_close_static()["passed"] is True


def test_run_pr_blocking_includes_meta() -> None:
    out = run_reasoning_gp06_pr_blocking_static_stages_v1()
    assert out["passed"] is True
    assert "meta_results" in out
    assert len(out["results"]) >= 1


def test_close01_shape_reference() -> None:
    r = verify_gp06_close01_tcre_cert_pack_shape_reference_static()
    assert r["id"] == "G-P06-CLOSE-01"
    assert r["passed"] is True
    d = r["detail"]
    assert d["tcre_cert_pack_format_literal_v1"] == TCRE_CERT_PACK_FORMAT_LITERAL_V1
    assert d["tcre_cert_pack_manifest_format_key_v1"] == TCRE_CERT_PACK_MANIFEST_FORMAT_KEY_V1
    assert d["required_root_files_v1"] == OCTS_CERT_PACK_REQUIRED_ROOT_FILES_V1


def test_stage_z_orders_close_last() -> None:
    body = run_reasoning_gp06_wired_verification_stages_v1(("Z",))
    assert body["passed"] is True
    assert len(body["results"]) == 1
    assert body["results"][0]["gate_id"] == "G-P06-CLOSE-01"
