"""P06-25 — Reasoning receipts + proof artifacts (§1 types + §2 hashing)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.chronology_degradation_propagation import CD_CHRON
from vector.domains.cortex.reasoning.organizational_continuity_reasoning import AMB_NONE
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    PHASE06_REASONING_RECEIPTS_PROOF_ARTIFACTS_RUNTIME_SCHEMA_VERSION,
    REASONING_AMBIGUITY_RECEIPT_TYPE,
    REASONING_CANON_VERSION_V1,
    REASONING_CAUSAL_RECEIPT_TYPE,
    REASONING_EQUIVALENCE_RECEIPT_TYPE,
    REASONING_RECEIPT_TYPES_V1,
    ReasoningReceiptsProofArtifactsError,
    hash_reasoning_canonical_json_sha256_v1,
    reasoning_ambiguity_receipt_body_v1,
    reasoning_causal_receipt_body_v1,
    reasoning_equivalence_receipt_body_v1,
    validate_reasoning_receipt_type_literal_v1,
    verify_gp06_rra01_receipt_type_catalog_oracle_static,
    verify_gp06_rra02_canonical_hash_stable_under_key_order_static,
    verify_gp06_rra03_causal_receipt_sorted_ids_enforced_static,
    verify_gp06_rra04_ambiguity_receipt_happy_path_static,
    verify_gp06_rra05_equivalence_receipt_happy_path_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_REASONING_RECEIPTS_PROOF_ARTIFACTS_RUNTIME_SCHEMA_VERSION >= 1
    assert REASONING_CANON_VERSION_V1 >= 1


def test_static_gates() -> None:
    assert verify_gp06_rra01_receipt_type_catalog_oracle_static()["passed"] is True
    assert verify_gp06_rra02_canonical_hash_stable_under_key_order_static()["passed"] is True
    assert verify_gp06_rra03_causal_receipt_sorted_ids_enforced_static()["passed"] is True
    assert verify_gp06_rra04_ambiguity_receipt_happy_path_static()["passed"] is True
    assert verify_gp06_rra05_equivalence_receipt_happy_path_static()["passed"] is True


def test_receipt_types_count() -> None:
    assert len(REASONING_RECEIPT_TYPES_V1) == 6
    assert REASONING_CAUSAL_RECEIPT_TYPE == "reasoning_causal_receipt"
    assert REASONING_AMBIGUITY_RECEIPT_TYPE == "reasoning_ambiguity_receipt"
    assert REASONING_EQUIVALENCE_RECEIPT_TYPE == "reasoning_equivalence_receipt"


def test_validate_receipt_type_literal() -> None:
    validate_reasoning_receipt_type_literal_v1("reasoning_chronology_receipt")
    with pytest.raises(ReasoningReceiptsProofArtifactsError):
        validate_reasoning_receipt_type_literal_v1("unknown_receipt")


def test_causal_receipt_and_hash() -> None:
    body = reasoning_causal_receipt_body_v1(
        sorted_tcre_causal_edge_ids=["edge-a", "edge-z"],
        sorted_cd_codes=[CD_CHRON],
        causal_legality_class="causal_replay_equivalent",
    )
    assert body["receipt_type"] == REASONING_CAUSAL_RECEIPT_TYPE
    h = hash_reasoning_canonical_json_sha256_v1(body)
    assert len(h) == 64
    h2 = hash_reasoning_canonical_json_sha256_v1(dict(body))
    assert h == h2


def test_causal_receipt_rejects_duplicate_edge_id() -> None:
    with pytest.raises(ReasoningReceiptsProofArtifactsError, match="sorted"):
        reasoning_causal_receipt_body_v1(
            sorted_tcre_causal_edge_ids=["x", "x"],
            sorted_cd_codes=[],
            causal_legality_class="causal_replay_equivalent",
        )


def test_ambiguity_receipt() -> None:
    body = reasoning_ambiguity_receipt_body_v1(
        ambiguity_class_id=AMB_NONE,
        blocked_derivation_rules_hash="d" * 64,
    )
    assert body["receipt_type"] == REASONING_AMBIGUITY_RECEIPT_TYPE
    assert hash_reasoning_canonical_json_sha256_v1(body)


def test_equivalence_receipt() -> None:
    body = reasoning_equivalence_receipt_body_v1(
        double_run_digest_a="e" * 64,
        double_run_digest_b="f" * 64,
    )
    assert body["receipt_type"] == REASONING_EQUIVALENCE_RECEIPT_TYPE


def test_blocked_rules_hash_uppercase_rejected() -> None:
    with pytest.raises(ReasoningReceiptsProofArtifactsError, match="lowercase"):
        reasoning_ambiguity_receipt_body_v1(
            ambiguity_class_id=AMB_NONE,
            blocked_derivation_rules_hash="A" * 64,
        )


def test_doctrine_file_exists() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "reasoning-receipts-and-proof-artifacts.md"
        if p.is_file():
            txt = p.read_text(encoding="utf-8")
            assert "Canonical JSON" in txt or "canonical JSON" in txt
            assert "reasoning_chronology_receipt" in txt
            return
    pytest.fail("reasoning-receipts-and-proof-artifacts.md not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.REASONING_CANON_VERSION_V1 >= 1
    assert len(r.REASONING_RECEIPT_TYPES_V1) == 6
    assert verify_gp06_rra01_receipt_type_catalog_oracle_static()["passed"] is True
