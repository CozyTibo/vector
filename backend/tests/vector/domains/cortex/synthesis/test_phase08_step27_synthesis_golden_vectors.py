"""P08-27 — Synthesis golden vectors + policy fixture binding."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.synthesis.normative import (
    PHASE08_POLICY_PACK_FIXTURE_REF_V1,
    build_phase08_normative_program_document_v1,
)
from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
    PHASE08_SYNTHESIS_GOLDEN_VECTORS_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_GOLDEN_CORPUS_ID_V1,
    SYNTHESIS_GOLDEN_CORPUS_SCHEMA_VERSION_V1,
    SYNTHESIS_GOLDEN_VECTORS_SPEC_REF_V1,
    bind_synthesis_golden_corpus_at_root_v1,
    build_synthesis_golden_vectors_catalog_v1,
    hash_synthesis_corpus_manifest_digest_v1,
    hash_synthesis_policy_pack_fixture_file_v1,
    load_synthesis_corpus_manifest_v1,
    load_synthesis_golden_case_v1,
    load_synthesis_policy_pack_fixture_v1,
    run_synthesis_golden_case_v1,
    synthesis_golden_corpus_case_count_v1,
    synthesis_golden_vectors_v1_root,
    synthesis_policy_pack_fixture_path_v1,
    verify_gp08_gtc01_corpus_manifest_shape_static,
    verify_gp08_gtc01_synthesis_golden_vectors_static_bundle,
    verify_gp08_gtc02_replay_double_run_case_static,
    verify_gp08_gtc03_degraded_rd_upstream_case_static,
    verify_gp08_gtc04_empty_scope_legality_case_static,
    verify_gp08_gtc05_policy_pack_fixture_digest_static,
    verify_gp08_gtc06_full_bind_roundtrip_static,
    verify_gp08_gtc07_admin_openapi_path_matrix_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "fixtures" / "SynthesisPolicyPackV1_Default.json"
        if marker.is_file():
            return root
    msg = "repo root not found"
    raise RuntimeError(msg)


def test_runtime_constants() -> None:
    assert PHASE08_SYNTHESIS_GOLDEN_VECTORS_RUNTIME_SCHEMA_VERSION >= 1
    assert "phase-08-evaluation-quality-governance" in SYNTHESIS_GOLDEN_VECTORS_SPEC_REF_V1


def test_golden_vectors_root_and_manifest() -> None:
    root = synthesis_golden_vectors_v1_root()
    assert (root / "corpus_manifest.json").is_file()
    manifest = load_synthesis_corpus_manifest_v1()
    assert manifest["corpus_id"] == SYNTHESIS_GOLDEN_CORPUS_ID_V1
    assert manifest["corpus_schema_version"] == SYNTHESIS_GOLDEN_CORPUS_SCHEMA_VERSION_V1
    assert synthesis_golden_corpus_case_count_v1() == 4


def test_policy_pack_fixture_present_and_digest_stable() -> None:
    path = synthesis_policy_pack_fixture_path_v1()
    assert path.is_file()
    pack = load_synthesis_policy_pack_fixture_v1()
    assert pack["synthesis_policy_pack_id"] == "SynthesisPolicyPackV1_Default"
    h1 = hash_synthesis_policy_pack_fixture_file_v1()
    h2 = hash_synthesis_policy_pack_fixture_file_v1()
    assert h1 == h2
    assert len(h1) == 64


def test_normative_program_pins_fixture_digest() -> None:
    doc = build_phase08_normative_program_document_v1()
    assert doc["policy_pack_fixture_ref"] == PHASE08_POLICY_PACK_FIXTURE_REF_V1
    assert doc["policy_pack_fixture_digest_sha256"] == hash_synthesis_policy_pack_fixture_file_v1()


def test_manifest_digest_stable() -> None:
    manifest = load_synthesis_corpus_manifest_v1()
    assert hash_synthesis_corpus_manifest_digest_v1(manifest) == hash_synthesis_corpus_manifest_digest_v1(
        manifest,
    )


def test_all_gtc_oracles_pass() -> None:
    assert verify_gp08_gtc01_corpus_manifest_shape_static()["passed"] is True
    assert verify_gp08_gtc02_replay_double_run_case_static()["passed"] is True
    assert verify_gp08_gtc03_degraded_rd_upstream_case_static()["passed"] is True
    assert verify_gp08_gtc04_empty_scope_legality_case_static()["passed"] is True
    assert verify_gp08_gtc05_policy_pack_fixture_digest_static()["passed"] is True
    assert verify_gp08_gtc06_full_bind_roundtrip_static()["passed"] is True
    assert verify_gp08_gtc07_admin_openapi_path_matrix_static()["passed"] is True
    assert verify_gp08_gtc01_synthesis_golden_vectors_static_bundle()["passed"] is True


def test_bind_roundtrip() -> None:
    out = bind_synthesis_golden_corpus_at_root_v1()
    assert out["corpus_id"] == SYNTHESIS_GOLDEN_CORPUS_ID_V1
    assert len(out["cases_bound"]) == 4
    assert len(out["policy_pack_fixture_digest_sha256"]) == 64


def test_run_individual_golden_cases() -> None:
    replay = load_synthesis_golden_case_v1("replay_equivalence/double_run_v1")
    assert run_synthesis_golden_case_v1(replay)["gp08_replay_proof_passed"] is True
    degraded = load_synthesis_golden_case_v1("degradation/degraded_brief_rd_upstream_v1")
    assert run_synthesis_golden_case_v1(degraded)["synthesis_legality_class"] == "synthesis_degraded"
    empty = load_synthesis_golden_case_v1("legality/empty_scope_v1")
    assert run_synthesis_golden_case_v1(empty)["synthesis_legality_class"] == "synthesis_replay_safe"
    causal = load_synthesis_golden_case_v1("pipeline/causal_minimal_v1")
    assert run_synthesis_golden_case_v1(causal)["synthesis_workload_class"] == "execution_understanding"


def test_catalog_builder() -> None:
    cat = build_synthesis_golden_vectors_catalog_v1()
    assert cat["surface_kind"] == "doctrine_catalog"
    assert cat["golden_corpus_case_count"] == 4
    assert cat["policy_pack_fixture_present"] is True


def test_doctrine_fixture_file_present() -> None:
    root = _repo_root()
    assert (
        root / "DOCS" / "cortex" / "synthesis" / "fixtures" / "SynthesisPolicyPackV1_Default.json"
    ).is_file()
