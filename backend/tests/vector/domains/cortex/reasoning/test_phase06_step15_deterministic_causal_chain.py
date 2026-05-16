"""P06-15 — Deterministic causal chains (``causal_chain_id`` + policy digest)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.chronology_legality import TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
from vector.domains.cortex.reasoning.deterministic_causal_chain import (
    PHASE06_DETERMINISTIC_CAUSAL_CHAIN_RUNTIME_SCHEMA_VERSION,
    DeterministicCausalChainError,
    causal_chain_id_canonical_body_v1,
    hash_causal_chain_id_v1,
    validate_tcre_policy_bundle_digest_shape_v1,
    verify_causal_chain_id_v1,
    verify_gp06_dcc01_causal_chain_id_permutation_invariant_static,
    verify_gp06_dcc02_policy_digest_participates_static,
    verify_gp06_dcc03_canonical_body_sorted_keys_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_DETERMINISTIC_CAUSAL_CHAIN_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_dcc01_causal_chain_id_permutation_invariant_static()["passed"] is True
    assert verify_gp06_dcc02_policy_digest_participates_static()["passed"] is True
    assert verify_gp06_dcc03_canonical_body_sorted_keys_static()["passed"] is True


def test_digest_shape_rejects_uppercase() -> None:
    with pytest.raises(DeterministicCausalChainError, match="lowercase"):
        validate_tcre_policy_bundle_digest_shape_v1("A" * 64)


def test_digest_shape_accepts_fixture_digest() -> None:
    validate_tcre_policy_bundle_digest_shape_v1(TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST)


def test_hash_stable_with_default_fixture_digest() -> None:
    h = hash_causal_chain_id_v1(
        tcre_causal_edge_ids=["tcre_edge_alpha", "tcre_edge_beta"],
        reasoning_rule_pack_id="ReasoningRulePackV1_Default",
        tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
        tenant_id="tenant-7",
    )
    assert len(h) == 64
    verify_causal_chain_id_v1(
        causal_chain_id=h,
        tcre_causal_edge_ids=["tcre_edge_beta", "tcre_edge_alpha"],
        reasoning_rule_pack_id="ReasoningRulePackV1_Default",
        tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
        tenant_id="tenant-7",
    )


def test_verify_rejects_wrong_id() -> None:
    h = hash_causal_chain_id_v1(
        tcre_causal_edge_ids=["e1"],
        reasoning_rule_pack_id="p",
        tcre_policy_bundle_digest="f" * 64,
        tenant_id="t",
    )
    with pytest.raises(DeterministicCausalChainError, match="mismatch"):
        verify_causal_chain_id_v1(
            causal_chain_id="0" * 64,
            tcre_causal_edge_ids=["e1"],
            reasoning_rule_pack_id="p",
            tcre_policy_bundle_digest="f" * 64,
            tenant_id="t",
        )
    assert h != "0" * 64


def test_canonical_body_includes_digest() -> None:
    body = causal_chain_id_canonical_body_v1(
        tcre_causal_edge_ids=["z", "a"],
        reasoning_rule_pack_id="rp",
        tcre_policy_bundle_digest="a" * 64,
        tenant_id="tn",
    )
    assert body["tcre_policy_bundle_digest"] == "a" * 64
    assert body["tcre_causal_edge_ids"] == ["a", "z"]


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "deterministic-causal-chain-spec.md"
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "causal_chain_id" in text
            assert "tcre_policy_bundle_digest" in text
            return
    pytest.fail("deterministic-causal-chain-spec.md not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_DETERMINISTIC_CAUSAL_CHAIN_RUNTIME_SCHEMA_VERSION >= 1
    assert callable(r.hash_causal_chain_id_v1)
    assert callable(r.verify_causal_chain_id_v1)
