"""P06-09 — Replay chronology semantics (pinned tuple + permutation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.chronology_legality import TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
from vector.domains.cortex.reasoning.replay_chronology import (
    PHASE06_REPLAY_CHRONOLOGY_RUNTIME_SCHEMA_VERSION,
    REASONING_REPLAY_PERMUTATION_PROFILE_ID,
    REASONING_REPLAY_RECEIPT_TYPE,
    REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
    ReplayChronologyError,
    canonical_reasoning_replay_permutation_v1_json,
    hash_pinned_replay_chronology_tuple_v1,
    reasoning_replay_receipt_body_v1,
    validate_chronology_snapshot_matches_pinned_replay_tuple_v1,
    validate_pinned_replay_chronology_tuple_v1,
    validate_reasoning_replay_permutation_v1_json,
    verify_gp06_rep01_permutation_canonical_static,
    verify_gp06_rep02_pinned_tuple_hash_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_REPLAY_CHRONOLOGY_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp06_rep01_static() -> None:
    assert verify_gp06_rep01_permutation_canonical_static()["passed"] is True


def test_verify_gp06_rep02_static() -> None:
    assert verify_gp06_rep02_pinned_tuple_hash_static()["passed"] is True


def test_partition_keys_sorted_in_canonical_json() -> None:
    js = canonical_reasoning_replay_permutation_v1_json(["z", "a"])
    obj = validate_reasoning_replay_permutation_v1_json(js)
    assert obj["partition_keys_sorted"] == ["a", "z"]


def test_permutation_rejects_unsorted_json() -> None:
    bad = '{"partition_keys_sorted":["b","a"],"profile_id":"reasoning_replay_permutation_v1","shuffle_independent_partitions":true,"within_partition_reverse":false}'
    with pytest.raises(ReplayChronologyError, match="sorted"):
        validate_reasoning_replay_permutation_v1_json(bad)


def test_permutation_rejects_non_canonical_whitespace() -> None:
    obj = {
        "partition_keys_sorted": ["x"],
        "profile_id": REASONING_REPLAY_PERMUTATION_PROFILE_ID,
        "shuffle_independent_partitions": True,
        "within_partition_reverse": False,
    }
    import json

    loose = json.dumps(obj, sort_keys=True)  # includes default separators with spaces
    with pytest.raises(ReplayChronologyError, match="canonical"):
        validate_reasoning_replay_permutation_v1_json(loose)


def test_pinned_tuple_round_trip_digest_stable() -> None:
    perm = canonical_reasoning_replay_permutation_v1_json(["p1", "p2"])
    pinned = validate_pinned_replay_chronology_tuple_v1(
        raw_evidence_bundle_digest="sha256:" + "c" * 64,
        reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
        tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
        reasoning_replay_permutation_v1=perm,
        walk_result_hash=REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
    )
    d1 = hash_pinned_replay_chronology_tuple_v1(pinned)
    d2 = hash_pinned_replay_chronology_tuple_v1(pinned)
    assert d1 == d2
    assert len(d1) == 64


def test_bridge_matches_optional_snapshot_fields() -> None:
    perm = canonical_reasoning_replay_permutation_v1_json(["only"])
    pinned = validate_pinned_replay_chronology_tuple_v1(
        raw_evidence_bundle_digest="sha256:" + "d" * 64,
        reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
        tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
        reasoning_replay_permutation_v1=perm,
        walk_result_hash="walk:abc",
    )
    validate_chronology_snapshot_matches_pinned_replay_tuple_v1(
        pinned_tuple=pinned,
        chronology_projection_snapshot={
            "replay_safe_ordering": "strict",
            "skew_detected": False,
            "late_arrival": False,
            "export_sequence_conflict": False,
            "tcre_policy_bundle_digest": TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
            "reasoning_rule_pack_id": "ReasoningPolicyPackV1_Default",
        },
    )


def test_bridge_rejects_digest_mismatch() -> None:
    perm = canonical_reasoning_replay_permutation_v1_json(["only"])
    pinned = validate_pinned_replay_chronology_tuple_v1(
        raw_evidence_bundle_digest="sha256:" + "e" * 64,
        reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
        tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
        reasoning_replay_permutation_v1=perm,
        walk_result_hash=REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
    )
    with pytest.raises(ReplayChronologyError, match="tcre_policy_bundle_digest"):
        validate_chronology_snapshot_matches_pinned_replay_tuple_v1(
            pinned_tuple=pinned,
            chronology_projection_snapshot={
                "tcre_policy_bundle_digest": "0" * 64,
            },
        )


def test_reasoning_replay_receipt_body() -> None:
    perm = canonical_reasoning_replay_permutation_v1_json(["x"])
    pinned = validate_pinned_replay_chronology_tuple_v1(
        raw_evidence_bundle_digest="sha256:" + "f" * 64,
        reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
        tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
        reasoning_replay_permutation_v1=perm,
        walk_result_hash=REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
    )
    body = reasoning_replay_receipt_body_v1(pinned_tuple=pinned, index_content_hash="idx:1")
    assert body["receipt_type"] == REASONING_REPLAY_RECEIPT_TYPE
    assert body["index_content_hash"] == "idx:1"


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p1 = root / "DOCS" / "cortex" / "reasoning" / "replay-aware-reasoning-law.md"
        p2 = root / "DOCS" / "cortex" / "reasoning" / "replay-equivalence-reasoning-spec.md"
        if p1.is_file() and p2.is_file():
            t1, t2 = p1.read_text(encoding="utf-8"), p2.read_text(encoding="utf-8")
            assert "reasoning_replay_permutation_v1" in t2
            assert "walk_result_hash" in t1 or "__NO_WALK_INPUT__" in t1
            return
    pytest.fail("doctrine files not found")


def test_package_reexports() -> None:
    from vector.domains.cortex.reasoning import (
        REPLAY_PINNED_WALK_NO_INPUT_SENTINEL as sentinel,
        canonical_reasoning_replay_permutation_v1_json as canon,
    )

    assert sentinel == "__NO_WALK_INPUT__"
    assert REASONING_REPLAY_PERMUTATION_PROFILE_ID in canon(["a"])
