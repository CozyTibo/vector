"""P06-30 — Golden-thread corpus binding (on-disk vectors + AMB/CD/TCRE expectations)."""

from __future__ import annotations

import pytest

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import (
    EXECUTION_RECONSTRUCTION_CONTRACT_VERSION,
)
from vector.domains.cortex.reasoning.causal_ambiguity_propagation import (
    normalize_ambiguity_corpus_token_to_registry_id_v1,
)
from vector.domains.cortex.reasoning.chronology_degradation_propagation import (
    CD_CHRON,
    CD_CONT,
    normalize_expected_degradation_classes_corpus_v1,
)
from vector.domains.cortex.reasoning.organizational_continuity_reasoning import (
    AMB_CHRON_PARTIAL,
    AMB_NONE,
)
from vector.domains.cortex.reasoning.reasoning_golden_thread_binding import (
    GOLDEN_THREAD_REPLAY_CORPUS_SPEC_REF_V1,
    PHASE06_REASONING_GOLDEN_THREAD_BINDING_RUNTIME_SCHEMA_VERSION,
    REASONING_GOLDEN_THREAD_CORPUS_SCHEMA_VERSION_V1,
    ReasoningGoldenThreadCorpusBindingError,
    bind_reasoning_golden_corpus_at_root_v1,
    hash_reasoning_corpus_manifest_digest_v1,
    load_reasoning_corpus_case_v1,
    load_reasoning_corpus_manifest_v1,
    reasoning_golden_vectors_v1_root,
    validate_reasoning_corpus_manifest_v1,
    verify_gp06_gtc01_default_manifest_shape_static,
    verify_gp06_gtc02_case_ambiguity_binding_static,
    verify_gp06_gtc03_case_degradation_cd_binding_static,
    verify_gp06_gtc04_optional_tcre_chains_shape_static,
    verify_gp06_gtc05_full_bind_roundtrip_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_REASONING_GOLDEN_THREAD_BINDING_RUNTIME_SCHEMA_VERSION >= 1
    assert "golden-thread-replay-corpus" in GOLDEN_THREAD_REPLAY_CORPUS_SPEC_REF_V1


def test_static_gates() -> None:
    assert verify_gp06_gtc01_default_manifest_shape_static()["passed"] is True
    assert verify_gp06_gtc02_case_ambiguity_binding_static()["passed"] is True
    assert verify_gp06_gtc03_case_degradation_cd_binding_static()["passed"] is True
    assert verify_gp06_gtc04_optional_tcre_chains_shape_static()["passed"] is True
    assert verify_gp06_gtc05_full_bind_roundtrip_static()["passed"] is True


def test_reasoning_golden_vectors_root_exists() -> None:
    root = reasoning_golden_vectors_v1_root()
    assert (root / "corpus_manifest.json").is_file()
    assert (root / "cases" / "tcre_ambiguity_cd_minimal_v1" / "case.json").is_file()


def test_manifest_contract_version_matches_code() -> None:
    root = reasoning_golden_vectors_v1_root()
    manifest = load_reasoning_corpus_manifest_v1(root / "corpus_manifest.json")
    ecv = manifest["execution_reconstruction_contract_version"]
    assert ecv == EXECUTION_RECONSTRUCTION_CONTRACT_VERSION
    assert manifest["corpus_schema_version"] == REASONING_GOLDEN_THREAD_CORPUS_SCHEMA_VERSION_V1


def test_manifest_digest_stable() -> None:
    root = reasoning_golden_vectors_v1_root()
    manifest = load_reasoning_corpus_manifest_v1(root / "corpus_manifest.json")
    h1 = hash_reasoning_corpus_manifest_digest_v1(manifest)
    h2 = hash_reasoning_corpus_manifest_digest_v1(manifest)
    assert h1 == h2
    assert len(h1) == 64


def test_case_ambiguity_and_degradation_normalization() -> None:
    root = reasoning_golden_vectors_v1_root()
    cpath = root / "cases" / "tcre_ambiguity_cd_minimal_v1" / "case.json"
    case = load_reasoning_corpus_case_v1(cpath)
    amb = case["expected_ambiguity_classes"]
    assert normalize_ambiguity_corpus_token_to_registry_id_v1(amb[0]) == AMB_CHRON_PARTIAL
    assert normalize_ambiguity_corpus_token_to_registry_id_v1(amb[1]) == AMB_NONE
    deg = normalize_expected_degradation_classes_corpus_v1(case["expected_degradation_classes"])
    assert deg == sorted({CD_CONT, CD_CHRON})


def test_bind_roundtrip() -> None:
    out = bind_reasoning_golden_corpus_at_root_v1()
    assert out["corpus_id"] == "tcre_golden_thread_v1"
    assert out["cases_bound"] == ("tcre_ambiguity_cd_minimal_v1",)
    assert len(out["manifest_digest_sha256"]) == 64


def test_validate_manifest_rejects_bad_contract_version() -> None:
    bad = {
        "corpus_id": "x",
        "corpus_schema_version": REASONING_GOLDEN_THREAD_CORPUS_SCHEMA_VERSION_V1,
        "reconstruction_version": "rv",
        "execution_reconstruction_contract_version": 999,
        "cases": [{"corpus_case_id": "c1"}],
    }
    with pytest.raises(ReasoningGoldenThreadCorpusBindingError, match="execution_reconstruction"):
        validate_reasoning_corpus_manifest_v1(bad)
