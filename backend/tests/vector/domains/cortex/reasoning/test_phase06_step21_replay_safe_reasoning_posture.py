"""P06-21 — Replay-safe reasoning posture (pinned tuple + policy digest)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.chronology_legality import (
    TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
)
from vector.domains.cortex.reasoning.replay_chronology import (
    REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
    canonical_reasoning_replay_permutation_v1_json,
    hash_pinned_replay_chronology_tuple_v1,
)
from vector.domains.cortex.reasoning.replay_safe_reasoning_posture import (
    PHASE06_REPLAY_SAFE_REASONING_POSTURE_RUNTIME_SCHEMA_VERSION,
    ReplaySafeReasoningPostureError,
    validate_replay_safe_reasoning_posture_from_mapping_v1,
    validate_replay_safe_reasoning_posture_v1,
    verify_gp06_rsp01_replay_safe_posture_happy_path_static,
    verify_gp06_rsp02_policy_digest_shape_rejected_static,
    verify_gp06_rsp03_permutation_profile_id_enforced_static,
    verify_gp06_rsp04_pinned_tuple_hash_stable_under_posture_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_REPLAY_SAFE_REASONING_POSTURE_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_rsp01_replay_safe_posture_happy_path_static()["passed"] is True
    assert verify_gp06_rsp02_policy_digest_shape_rejected_static()["passed"] is True
    assert verify_gp06_rsp03_permutation_profile_id_enforced_static()["passed"] is True
    assert verify_gp06_rsp04_pinned_tuple_hash_stable_under_posture_static()["passed"] is True


def test_digest_shape_wrapped_error() -> None:
    perm = canonical_reasoning_replay_permutation_v1_json(["p"])
    with pytest.raises(ReplaySafeReasoningPostureError, match="tcre_policy_bundle_digest"):
        validate_replay_safe_reasoning_posture_v1(
            raw_evidence_bundle_digest="sha256:" + "a" * 64,
            reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
            tcre_policy_bundle_digest="NOT_HEX",
            reasoning_replay_permutation_v1=perm,
            walk_result_hash=REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
        )


def test_validate_from_mapping() -> None:
    perm = canonical_reasoning_replay_permutation_v1_json(["q"])
    pinned = {
        "raw_evidence_bundle_digest": "sha256:" + "b" * 64,
        "reasoning_rule_pack_id": "ReasoningPolicyPackV1_Default",
        "tcre_policy_bundle_digest": TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
        "reasoning_replay_permutation_v1": perm,
        "walk_result_hash": REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
    }
    out = validate_replay_safe_reasoning_posture_from_mapping_v1(pinned)
    assert out["tcre_policy_bundle_digest"] == TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST


def test_from_mapping_rejects_extra_keys() -> None:
    perm = canonical_reasoning_replay_permutation_v1_json(["r"])
    bad = {
        "raw_evidence_bundle_digest": "sha256:" + "c" * 64,
        "reasoning_rule_pack_id": "ReasoningPolicyPackV1_Default",
        "tcre_policy_bundle_digest": TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
        "reasoning_replay_permutation_v1": perm,
        "walk_result_hash": REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
        "extra": 1,
    }
    with pytest.raises(ReplaySafeReasoningPostureError, match="exactly keys"):
        validate_replay_safe_reasoning_posture_from_mapping_v1(bad)


def test_same_posture_same_hash() -> None:
    perm = canonical_reasoning_replay_permutation_v1_json(["s"])
    pinned = validate_replay_safe_reasoning_posture_v1(
        raw_evidence_bundle_digest="sha256:" + "d" * 64,
        reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
        tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
        reasoning_replay_permutation_v1=perm,
        walk_result_hash=REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
    )
    assert hash_pinned_replay_chronology_tuple_v1(pinned) == hash_pinned_replay_chronology_tuple_v1(
        pinned
    )


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        law = root / "DOCS" / "cortex" / "reasoning" / "replay-aware-reasoning-law.md"
        if law.is_file():
            t = law.read_text(encoding="utf-8")
            assert "tcre_policy_bundle_digest" in t
            assert "reasoning_replay_permutation_v1" in t
            pol = root / "DOCS" / "cortex" / "reasoning" / "reasoning-policy-pack-v1.md"
            assert pol.is_file()
            assert "tcre_policy_bundle_digest" in pol.read_text(encoding="utf-8")
            return
    pytest.fail("P06-21 doctrine files not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_REPLAY_SAFE_REASONING_POSTURE_RUNTIME_SCHEMA_VERSION >= 1
    assert callable(r.validate_replay_safe_reasoning_posture_v1)
    assert verify_gp06_rsp01_replay_safe_posture_happy_path_static()["passed"] is True
