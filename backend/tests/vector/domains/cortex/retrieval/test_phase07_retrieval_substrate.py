"""Phase 07 retrieval substrate unit tests."""

from __future__ import annotations

from vector.domains.cortex.retrieval.retrieval_lookup_projection import derive_retrieval_lookup_id_v1
from vector.domains.cortex.retrieval.retrieval_legality_projection import retrieval_policy_digest_v1


def test_retrieval_lookup_id_stable() -> None:
    a = derive_retrieval_lookup_id_v1(
        index_kind="causal_chain",
        index_key="causal_chain:abc",
        replay_identity="rid1",
    )
    b = derive_retrieval_lookup_id_v1(
        index_kind="causal_chain",
        index_key="causal_chain:abc",
        replay_identity="rid1",
    )
    assert a == b
    assert len(a) == 32


def test_policy_digest_stable() -> None:
    assert retrieval_policy_digest_v1() == retrieval_policy_digest_v1()
