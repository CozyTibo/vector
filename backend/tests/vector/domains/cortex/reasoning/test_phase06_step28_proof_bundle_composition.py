"""P06-28 — Proof bundle composition (inner digest + equivalence receipt set)."""

from __future__ import annotations

import pytest

from vector.domains.cortex.reasoning.proof_bundle_composition import (
    PHASE06_PROOF_BUNDLE_COMPOSITION_RUNTIME_SCHEMA_VERSION,
    PROOF_BUNDLE_COMPOSITION_SPEC_REF_V1,
    ProofBundleCompositionError,
    build_proof_bundle_inner_digest_body_v1,
    hash_proof_bundle_inner_digest_v1,
    validate_proof_bundle_equivalence_receipt_set_v1,
    verify_gp06_pbc01_inner_body_sorted_pairs_oracle_static,
    verify_gp06_pbc02_equivalence_receipt_always_required_static,
    verify_gp06_pbc03_chronology_required_when_participates_static,
    verify_gp06_pbc04_inner_hash_permutation_invariant_static,
    verify_gp06_pbc05_full_minimal_bundle_validates_static,
)
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    REASONING_AMBIGUITY_RECEIPT_TYPE,
    REASONING_CAUSAL_RECEIPT_TYPE,
    REASONING_CHRONOLOGY_RECEIPT_TYPE,
    REASONING_EQUIVALENCE_RECEIPT_TYPE,
    REASONING_REPLAY_RECEIPT_TYPE,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_PROOF_BUNDLE_COMPOSITION_RUNTIME_SCHEMA_VERSION >= 1
    assert "reasoning-receipts-and-proof-artifacts" in PROOF_BUNDLE_COMPOSITION_SPEC_REF_V1


def test_static_gates() -> None:
    assert verify_gp06_pbc01_inner_body_sorted_pairs_oracle_static()["passed"] is True
    assert verify_gp06_pbc02_equivalence_receipt_always_required_static()["passed"] is True
    assert verify_gp06_pbc03_chronology_required_when_participates_static()["passed"] is True
    assert verify_gp06_pbc04_inner_hash_permutation_invariant_static()["passed"] is True
    assert verify_gp06_pbc05_full_minimal_bundle_validates_static()["passed"] is True


def test_inner_body_shape_and_sort() -> None:
    d = "0" * 64
    body = build_proof_bundle_inner_digest_body_v1(
        receipt_type_digest_pairs=[
            (REASONING_EQUIVALENCE_RECEIPT_TYPE, d),
            (REASONING_CAUSAL_RECEIPT_TYPE, d),
        ],
    )
    assert set(body.keys()) == {"reasoning_canon_version_v1", "receipt_pairs_sorted"}
    assert body["receipt_pairs_sorted"][0]["receipt_type"] == REASONING_CAUSAL_RECEIPT_TYPE


def test_inner_digest_rejects_bad_digest() -> None:
    with pytest.raises(ProofBundleCompositionError, match="sha256"):
        build_proof_bundle_inner_digest_body_v1(
            receipt_type_digest_pairs=[
                (REASONING_CAUSAL_RECEIPT_TYPE, "not-a-hash"),
                (REASONING_EQUIVALENCE_RECEIPT_TYPE, "a" * 64),
            ],
        )


def test_validate_chronology_ambiguity_replay_flags() -> None:
    d = "1" * 64
    base = [
        (REASONING_CAUSAL_RECEIPT_TYPE, d),
        (REASONING_EQUIVALENCE_RECEIPT_TYPE, d),
    ]
    validate_proof_bundle_equivalence_receipt_set_v1(
        receipt_type_digest_pairs=base + [(REASONING_CHRONOLOGY_RECEIPT_TYPE, d)],
        chronology_participates=True,
        ambiguity_active=False,
        walk_consumed=False,
    )
    validate_proof_bundle_equivalence_receipt_set_v1(
        receipt_type_digest_pairs=base
        + [(REASONING_CHRONOLOGY_RECEIPT_TYPE, d), (REASONING_AMBIGUITY_RECEIPT_TYPE, d)],
        chronology_participates=True,
        ambiguity_active=True,
        walk_consumed=False,
    )
    validate_proof_bundle_equivalence_receipt_set_v1(
        receipt_type_digest_pairs=base
        + [
            (REASONING_CHRONOLOGY_RECEIPT_TYPE, d),
            (REASONING_AMBIGUITY_RECEIPT_TYPE, d),
            (REASONING_REPLAY_RECEIPT_TYPE, d),
        ],
        chronology_participates=True,
        ambiguity_active=True,
        walk_consumed=True,
    )


def test_validate_rejects_missing_replay_when_walk_consumed() -> None:
    d = "2" * 64
    with pytest.raises(ProofBundleCompositionError, match="replay"):
        validate_proof_bundle_equivalence_receipt_set_v1(
            receipt_type_digest_pairs=[
                (REASONING_CAUSAL_RECEIPT_TYPE, d),
                (REASONING_EQUIVALENCE_RECEIPT_TYPE, d),
            ],
            chronology_participates=False,
            ambiguity_active=False,
            walk_consumed=True,
        )


def test_hash_stable_across_pair_order() -> None:
    d = "3" * 64
    pairs_a = [
        (REASONING_CAUSAL_RECEIPT_TYPE, d),
        (REASONING_EQUIVALENCE_RECEIPT_TYPE, d),
    ]
    pairs_b = list(reversed(pairs_a))
    assert hash_proof_bundle_inner_digest_v1(receipt_type_digest_pairs=pairs_a) == (
        hash_proof_bundle_inner_digest_v1(receipt_type_digest_pairs=pairs_b)
    )
