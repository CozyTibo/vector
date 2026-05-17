"""P07-27 — G-P07-* verification harness (catalog + wired runners)."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.retrieval.retrieval_verification_harness import (
    PHASE07_RETRIEVAL_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
    RETRIEVAL_CERT_PACK_REQUIRED_ROOT_FILES_V1,
    RETRIEVAL_GP07_CORRUPTION_BUNDLES_V1,
    RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1,
    RETRIEVAL_GP07_STAGE_A_GATE_IDS_V1,
    RETRIEVAL_GP07_STAGE_C_GATE_IDS_V1,
    RETRIEVAL_VERIFICATION_HARNESS_CATALOG_VERSION_V1,
    RETRIEVAL_VERIFICATION_HARNESS_SPEC_REF_V1,
    build_retrieval_verification_harness_catalog_v1,
    default_severity_for_retrieval_gate_v1,
    list_retrieval_gp07_doctrine_gate_ids_v1,
    list_retrieval_gp07_wired_verification_runners_v1,
    retrieval_gp07_gate_stage_v1,
    run_retrieval_gp07_ci_full_wired_stages_with_meta_v1,
    run_retrieval_gp07_pr_blocking_static_stages_v1,
    run_retrieval_gp07_stage_c_replay_gates_v1,
    run_retrieval_gp07_wired_verification_stages_v1,
    verify_gp07_close01_retrieval_cert_pack_closure_static,
    verify_gp07_rvh01_harness_catalog_covers_spec_gate_table_static,
    verify_gp07_rvh02_pr_blocking_bundle_passes_static,
    verify_gp07_rvh03_full_stage_az_includes_close_static,
    verify_retrieval_gp07_corruption_bundles_subset_static,
    verify_retrieval_gp07_gate_catalog_unique_ids_static,
    verify_retrieval_gp07_wired_runner_gate_ids_match_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-verification-harness-spec.md"
        if marker.is_file():
            return root
    msg = "repo root not found"
    raise RuntimeError(msg)


def test_runtime_constants() -> None:
    assert PHASE07_RETRIEVAL_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION >= 1
    assert RETRIEVAL_VERIFICATION_HARNESS_CATALOG_VERSION_V1 >= 1
    assert "phase-07-verification-harness-spec" in RETRIEVAL_VERIFICATION_HARNESS_SPEC_REF_V1
    assert RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1 == "RETRIEVAL-CERT-PACK-1"
    assert len(RETRIEVAL_CERT_PACK_REQUIRED_ROOT_FILES_V1) == 5


def test_doctrine_gate_ids_sorted_unique() -> None:
    assert verify_retrieval_gp07_gate_catalog_unique_ids_static()["passed"] is True
    assert list_retrieval_gp07_doctrine_gate_ids_v1() == RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1
    assert len(RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1) == 13


def test_corruption_bundles_subset() -> None:
    assert verify_retrieval_gp07_corruption_bundles_subset_static()["passed"] is True
    assert "replay_surface" in RETRIEVAL_GP07_CORRUPTION_BUNDLES_V1


def test_wired_runner_ids_match_catalog_keys() -> None:
    assert verify_retrieval_gp07_wired_runner_gate_ids_match_static()["passed"] is True
    runners = list_retrieval_gp07_wired_verification_runners_v1()
    assert set(runners.keys()) == set(RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1)


def test_gate_stages_and_severity() -> None:
    assert retrieval_gp07_gate_stage_v1("G-P07-ANTI-01") == "A"
    assert retrieval_gp07_gate_stage_v1("G-P07-REPLAY-01") == "C"
    assert retrieval_gp07_gate_stage_v1("G-P07-CLOSE-01") == "Z"
    assert retrieval_gp07_gate_stage_v1("unknown") is None
    assert default_severity_for_retrieval_gate_v1("G-P07-REPLAY-01") == "hard_fail"
    assert RETRIEVAL_GP07_STAGE_A_GATE_IDS_V1 == (
        "G-P07-ANTI-01",
        "G-P07-ANTI-02",
        "G-P07-SCHEMA-01",
    )
    assert RETRIEVAL_GP07_STAGE_C_GATE_IDS_V1 == ("G-P07-REPLAY-01", "G-P07-REPLAY-02")


def test_all_rvh_oracles_pass() -> None:
    assert verify_gp07_rvh01_harness_catalog_covers_spec_gate_table_static()["passed"] is True
    assert verify_gp07_rvh02_pr_blocking_bundle_passes_static()["passed"] is True
    assert verify_gp07_rvh03_full_stage_az_includes_close_static()["passed"] is True


def test_run_pr_blocking_includes_meta() -> None:
    out = run_retrieval_gp07_pr_blocking_static_stages_v1()
    assert out["passed"] is True
    assert out["stages"] == ["A", "B", "C"]
    assert "meta_results" in out
    assert len(out["stage_a"]) == 3
    assert len(out["stage_b"]) == 4


def test_stage_c_and_wired_stages() -> None:
    c = run_retrieval_gp07_stage_c_replay_gates_v1()
    assert c["passed"] is True
    assert c["stage"] == "C"
    d = run_retrieval_gp07_wired_verification_stages_v1(("D",))
    assert d["passed"] is True
    assert any(r["gate_id"] == "G-P07-CP-01" for r in d["results"])


def test_close01_shape_reference() -> None:
    r = verify_gp07_close01_retrieval_cert_pack_closure_static()
    assert r["id"] == "G-P07-CLOSE-01"
    assert r["passed"] is True
    assert r["detail"]["retrieval_cert_pack_format_literal_v1"] == RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1


def test_full_az_and_catalog_builder() -> None:
    body = run_retrieval_gp07_ci_full_wired_stages_with_meta_v1()
    assert body["passed"] is True
    cat = build_retrieval_verification_harness_catalog_v1()
    assert cat["pr_blocking_stages"] == ["A", "B", "C"]
    assert len(cat["gate_ids"]) == 13


def test_doctrine_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-verification-harness-spec.md").read_text(
        encoding="utf-8"
    )
    assert "run_retrieval_gp07_pr_blocking_static_stages_v1" in text
    assert "G-P07-CLOSE-01" in text
