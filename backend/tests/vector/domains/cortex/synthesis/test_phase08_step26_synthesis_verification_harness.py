"""P08-26 — Synthesis **G-P08-*** verification harness (catalog + wired runners)."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.synthesis.synthesis_verification_harness import (
    PHASE08_SYNTHESIS_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1,
    SYNTHESIS_CERT_PACK_REQUIRED_ROOT_FILES_V1,
    SYNTHESIS_GP08_CORRUPTION_BUNDLES_V1,
    SYNTHESIS_GP08_DOCTRINE_GATE_IDS_V1,
    SYNTHESIS_GP08_STAGE_A_GATE_IDS_V1,
    SYNTHESIS_GP08_STAGE_C_GATE_IDS_V1,
    SYNTHESIS_VERIFICATION_HARNESS_CATALOG_VERSION_V1,
    SYNTHESIS_VERIFICATION_HARNESS_SPEC_REF_V1,
    build_synthesis_verification_harness_catalog_v1,
    build_synthesis_verification_harness_receipt_v1,
    default_severity_for_synthesis_gate_v1,
    list_synthesis_gp08_doctrine_gate_ids_v1,
    list_synthesis_gp08_wired_verification_runners_v1,
    list_synthesis_harness_run_ledger_v1,
    run_synthesis_gp08_ci_full_wired_stages_with_meta_v1,
    run_synthesis_gp08_pr_blocking_static_stages_v1,
    run_synthesis_gp08_stage_c_replay_gates_v1,
    run_synthesis_gp08_wired_verification_stages_v1,
    synthesis_gp08_gate_stage_v1,
    verify_gp08_close01_synthesis_cert_pack_closure_static,
    verify_gp08_close01_synthesis_cert_pack_shape_reference_static,
    verify_gp08_rvh01_harness_catalog_covers_spec_gate_table_static,
    verify_gp08_rvh01_synthesis_verification_harness_static_bundle,
    verify_gp08_rvh02_pr_blocking_bundle_passes_static,
    verify_gp08_rvh03_full_stage_az_includes_close_static,
    verify_gp08_rvh04_admin_openapi_path_matrix_static,
    verify_synthesis_gp08_corruption_bundles_subset_static,
    verify_synthesis_gp08_gate_catalog_unique_ids_static,
    verify_synthesis_gp08_wired_runner_gate_ids_match_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-testing-strategy.md"
        if marker.is_file():
            return root
    msg = "repo root not found"
    raise RuntimeError(msg)


def test_runtime_constants() -> None:
    assert PHASE08_SYNTHESIS_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION >= 1
    assert SYNTHESIS_VERIFICATION_HARNESS_CATALOG_VERSION_V1 >= 1
    assert "phase-08-testing-strategy" in SYNTHESIS_VERIFICATION_HARNESS_SPEC_REF_V1
    assert SYNTHESIS_CERT_PACK_FORMAT_LITERAL_V1 == "SYNTHESIS-CERT-PACK-1"
    assert len(SYNTHESIS_CERT_PACK_REQUIRED_ROOT_FILES_V1) == 5


def test_doctrine_gate_ids_sorted_unique() -> None:
    assert verify_synthesis_gp08_gate_catalog_unique_ids_static()["passed"] is True
    assert list_synthesis_gp08_doctrine_gate_ids_v1() == SYNTHESIS_GP08_DOCTRINE_GATE_IDS_V1
    assert len(SYNTHESIS_GP08_DOCTRINE_GATE_IDS_V1) == 19


def test_corruption_bundles_subset() -> None:
    assert verify_synthesis_gp08_corruption_bundles_subset_static()["passed"] is True
    assert "replay_surface" in SYNTHESIS_GP08_CORRUPTION_BUNDLES_V1


def test_wired_runner_ids_match_catalog_keys() -> None:
    assert verify_synthesis_gp08_wired_runner_gate_ids_match_static()["passed"] is True
    runners = list_synthesis_gp08_wired_verification_runners_v1()
    assert set(runners.keys()) == set(SYNTHESIS_GP08_DOCTRINE_GATE_IDS_V1)


def test_gate_stages_and_severity() -> None:
    assert synthesis_gp08_gate_stage_v1("G-P08-ANTI-01") == "A"
    assert synthesis_gp08_gate_stage_v1("G-P08-REPLAY-01") == "C"
    assert synthesis_gp08_gate_stage_v1("G-P08-CLOSE-01") == "Z"
    assert synthesis_gp08_gate_stage_v1("unknown") is None
    assert default_severity_for_synthesis_gate_v1("G-P08-REPLAY-01") == "hard_fail"
    assert SYNTHESIS_GP08_STAGE_A_GATE_IDS_V1 == (
        "G-P08-ANTI-01",
        "G-P08-ANTI-02",
        "G-P08-SCHEMA-01",
    )
    assert SYNTHESIS_GP08_STAGE_C_GATE_IDS_V1 == ("G-P08-REPLAY-01", "G-P08-REPLAY-02")


def test_all_rvh_oracles_pass() -> None:
    assert verify_gp08_rvh01_harness_catalog_covers_spec_gate_table_static()["passed"] is True
    assert verify_gp08_rvh02_pr_blocking_bundle_passes_static()["passed"] is True
    assert verify_gp08_rvh03_full_stage_az_includes_close_static()["passed"] is True
    assert verify_gp08_rvh04_admin_openapi_path_matrix_static()["passed"] is True
    bundle = verify_gp08_rvh01_synthesis_verification_harness_static_bundle()
    assert bundle["passed"] is True


def test_run_pr_blocking_includes_meta() -> None:
    out = run_synthesis_gp08_pr_blocking_static_stages_v1(record_ledger=False)
    assert out["passed"] is True
    assert out["stages"] == ["A", "B", "C"]
    assert "meta_results" in out
    assert len(out["stage_a"]) == 3
    assert len(out["stage_b"]) == 8


def test_stage_c_and_wired_stages() -> None:
    c = run_synthesis_gp08_stage_c_replay_gates_v1()
    assert c["passed"] is True
    assert c["stage"] == "C"
    d = run_synthesis_gp08_wired_verification_stages_v1(("D",), record_ledger=False)
    assert d["passed"] is True
    assert any(r["gate_id"] == "G-P08-CP-01" for r in d["results"])


def test_close01_shape_and_closure() -> None:
    shape = verify_gp08_close01_synthesis_cert_pack_shape_reference_static()
    assert shape["id"] == "G-P08-CLOSE-01"
    assert shape["passed"] is True
    close = verify_gp08_close01_synthesis_cert_pack_closure_static()
    assert close["passed"] is True


def test_full_az_and_catalog_builder() -> None:
    body = run_synthesis_gp08_ci_full_wired_stages_with_meta_v1(record_ledger=False)
    assert body["passed"] is True
    cat = build_synthesis_verification_harness_catalog_v1()
    assert cat["pr_blocking_stages"] == ["A", "B", "C"]
    assert len(cat["gate_ids"]) == 19
    assert cat["surface_kind"] == "verification_probe"


def test_harness_receipt_and_ledger() -> None:
    before = len(list_synthesis_harness_run_ledger_v1())
    receipt = build_synthesis_verification_harness_receipt_v1(run_mode="pr_blocking")
    assert receipt["run_mode"] == "pr_blocking"
    assert receipt["harness_run"]["passed"] is True
    after = len(list_synthesis_harness_run_ledger_v1())
    assert after >= before


def test_doctrine_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "synthesis" / "phase-08-testing-strategy.md").read_text(
        encoding="utf-8"
    )
    assert "G-P08-ANTI-01" in text and "G-P08-REPLAY-01" in text
    assert "run_synthesis_gp08_pr_blocking_static_stages_v1" not in text
