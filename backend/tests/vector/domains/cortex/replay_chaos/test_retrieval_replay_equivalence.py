"""Replay chaos — retrieval legality fail-closed and equivalence."""

from __future__ import annotations

import pytest

from vector.domains.cortex.retrieval.retrieval_legality_projection import (
    RetrievalLegalityError,
    assert_retrieval_lawful_v1,
    classify_retrieval_legality_v1,
)


def test_classify_replay_safe() -> None:
    cls = classify_retrieval_legality_v1(
        replay_identity_match=True,
        chronology_legality_class="strict",
        causal_legality_class="verified",
        degradation_posture="stable",
        continuity_posture="stable",
        traversal_degraded=False,
    )
    assert cls == "retrieval_replay_safe"


def test_fail_closed_unverifiable() -> None:
    with pytest.raises(RetrievalLegalityError) as exc:
        assert_retrieval_lawful_v1(
            legality_class="retrieval_unverifiable",
            replay_posture="unsafe",
        )
    assert exc.value.code == "retrieval_fail_closed"


def test_degraded_still_queryable() -> None:
    assert_retrieval_lawful_v1(
        legality_class="retrieval_degraded",
        replay_posture="partial",
    )
