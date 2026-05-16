"""Phase 06 P06-21 — replay-safe reasoning posture (pinned tuple + policy digest law).

Normative:
``DOCS/cortex/reasoning/replay-aware-reasoning-law.md`` §1,
``DOCS/cortex/reasoning/reasoning-policy-pack-v1.md`` (``tcre_policy_bundle_digest`` §§1–2),
``DOCS/cortex/reasoning/replay-equivalence-reasoning-spec.md`` §3 (permutation profile id).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.reasoning.deterministic_causal_chain import (
    DeterministicCausalChainError,
    validate_tcre_policy_bundle_digest_shape_v1,
)
from vector.domains.cortex.reasoning.replay_chronology import (
    PHASE06_REPLAY_CHRONOLOGY_RUNTIME_SCHEMA_VERSION,
    REASONING_REPLAY_PERMUTATION_PROFILE_ID,
    REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
    ReplayChronologyError,
    canonical_reasoning_replay_permutation_v1_json,
    hash_pinned_replay_chronology_tuple_v1,
    validate_pinned_replay_chronology_tuple_v1,
)

PHASE06_REPLAY_SAFE_REASONING_POSTURE_RUNTIME_SCHEMA_VERSION: Final[int] = 1


class ReplaySafeReasoningPostureError(ValueError):
    """Fail-closed replay-safe posture (pinned tuple + ``tcre_policy_bundle_digest`` law)."""


def _rsp_detail(errors: list[str]) -> dict[str, Any]:
    return {
        "errors": errors,
        "phase06_replay_chronology_runtime_schema_version": (
            PHASE06_REPLAY_CHRONOLOGY_RUNTIME_SCHEMA_VERSION
        ),
        "phase06_replay_safe_reasoning_posture_runtime_schema_version": (
            PHASE06_REPLAY_SAFE_REASONING_POSTURE_RUNTIME_SCHEMA_VERSION
        ),
    }


def validate_replay_safe_reasoning_posture_v1(
    *,
    raw_evidence_bundle_digest: str,
    reasoning_rule_pack_id: str,
    tcre_policy_bundle_digest: str,
    reasoning_replay_permutation_v1: str,
    walk_result_hash: str,
) -> dict[str, Any]:
    """P06-21 — replay-aware §1 + policy-pack digest shape on pinned tuple (C)."""
    try:
        validate_tcre_policy_bundle_digest_shape_v1(tcre_policy_bundle_digest)
    except DeterministicCausalChainError as exc:
        raise ReplaySafeReasoningPostureError(str(exc)) from exc
    try:
        return validate_pinned_replay_chronology_tuple_v1(
            raw_evidence_bundle_digest=raw_evidence_bundle_digest,
            reasoning_rule_pack_id=reasoning_rule_pack_id,
            tcre_policy_bundle_digest=tcre_policy_bundle_digest,
            reasoning_replay_permutation_v1=reasoning_replay_permutation_v1,
            walk_result_hash=walk_result_hash,
        )
    except ReplayChronologyError as exc:
        raise ReplaySafeReasoningPostureError(str(exc)) from exc


def validate_replay_safe_reasoning_posture_from_mapping_v1(
    pinned_tuple: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate posture using a mapping with exactly the pinned tuple A–E keys."""
    keys = frozenset(pinned_tuple.keys())
    expected = frozenset(
        {
            "raw_evidence_bundle_digest",
            "reasoning_rule_pack_id",
            "tcre_policy_bundle_digest",
            "reasoning_replay_permutation_v1",
            "walk_result_hash",
        }
    )
    if keys != expected:
        raise ReplaySafeReasoningPostureError(
            "pinned_tuple must contain exactly keys A–E for replay-safe posture validation"
        )
    return validate_replay_safe_reasoning_posture_v1(
        raw_evidence_bundle_digest=str(pinned_tuple["raw_evidence_bundle_digest"]),
        reasoning_rule_pack_id=str(pinned_tuple["reasoning_rule_pack_id"]),
        tcre_policy_bundle_digest=str(pinned_tuple["tcre_policy_bundle_digest"]),
        reasoning_replay_permutation_v1=str(pinned_tuple["reasoning_replay_permutation_v1"]),
        walk_result_hash=str(pinned_tuple["walk_result_hash"]),
    )


def verify_gp06_rsp01_replay_safe_posture_happy_path_static() -> dict[str, Any]:
    """P06-21 — lawful digest + pinned tuple + canonical permutation."""
    errors: list[str] = []
    try:
        perm = canonical_reasoning_replay_permutation_v1_json(["a", "b"])
        validate_replay_safe_reasoning_posture_v1(
            raw_evidence_bundle_digest="sha256:" + "f" * 64,
            reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
            tcre_policy_bundle_digest="d48f77eb363cc2828b7af5351365d3e96dc5e1b4464c5fa1b6a5d6c56590f470",
            reasoning_replay_permutation_v1=perm,
            walk_result_hash=REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
        )
    except ReplaySafeReasoningPostureError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-21-rsp-happy-path",
        "name": "gp06_rsp01_replay_safe_posture_happy_path",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rsp_detail(errors),
    }


def verify_gp06_rsp02_policy_digest_shape_rejected_static() -> dict[str, Any]:
    """P06-21 — uppercase / non-sha256 digest fails before tuple acceptance."""
    errors: list[str] = []
    perm = canonical_reasoning_replay_permutation_v1_json(["x"])
    bad_digest = "D48F77EB363CC2828B7AF5351365D3E96DC5E1B4464C5FA1B6A5D6C56590F470"
    try:
        validate_replay_safe_reasoning_posture_v1(
            raw_evidence_bundle_digest="sha256:" + "0" * 64,
            reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
            tcre_policy_bundle_digest=bad_digest,
            reasoning_replay_permutation_v1=perm,
            walk_result_hash=REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
        )
    except ReplaySafeReasoningPostureError:
        pass
    else:
        errors.append("expected_reject_uppercase_policy_digest")
    passed = len(errors) == 0
    return {
        "id": "P06-21-rsp-digest-shape",
        "name": "gp06_rsp02_policy_digest_shape_rejected",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rsp_detail(errors),
    }


def verify_gp06_rsp03_permutation_profile_id_enforced_static() -> dict[str, Any]:
    """P06-21 — permutation JSON must declare ``reasoning_replay_permutation_v1`` profile."""
    errors: list[str] = []
    bad_perm = (
        '{"partition_keys_sorted":["z"],"profile_id":"wrong_profile",'
        '"shuffle_independent_partitions":true,"within_partition_reverse":false}'
    )
    try:
        validate_replay_safe_reasoning_posture_v1(
            raw_evidence_bundle_digest="sha256:" + "1" * 64,
            reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
            tcre_policy_bundle_digest="d48f77eb363cc2828b7af5351365d3e96dc5e1b4464c5fa1b6a5d6c56590f470",
            reasoning_replay_permutation_v1=bad_perm,
            walk_result_hash=REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
        )
    except ReplaySafeReasoningPostureError:
        pass
    else:
        errors.append("expected_reject_bad_permutation_profile_id")
    if REASONING_REPLAY_PERMUTATION_PROFILE_ID != "reasoning_replay_permutation_v1":
        errors.append("unexpected_permutation_profile_constant_drift")
    passed = len(errors) == 0
    return {
        "id": "P06-21-rsp-permutation-profile",
        "name": "gp06_rsp03_permutation_profile_id_enforced",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rsp_detail(errors),
    }


def verify_gp06_rsp04_pinned_tuple_hash_stable_under_posture_static() -> dict[str, Any]:
    """P06-21 — same validated posture ⇒ identical ``hash_pinned_replay_chronology_tuple_v1``."""
    errors: list[str] = []
    try:
        perm = canonical_reasoning_replay_permutation_v1_json(["k1"])
        pinned = validate_replay_safe_reasoning_posture_v1(
            raw_evidence_bundle_digest="sha256:" + "2" * 64,
            reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
            tcre_policy_bundle_digest="d48f77eb363cc2828b7af5351365d3e96dc5e1b4464c5fa1b6a5d6c56590f470",
            reasoning_replay_permutation_v1=perm,
            walk_result_hash=REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
        )
        d1 = hash_pinned_replay_chronology_tuple_v1(pinned)
        d2 = hash_pinned_replay_chronology_tuple_v1(pinned)
        if d1 != d2:
            errors.append("pinned_tuple_digest_unstable")
        if len(d1) != 64:
            errors.append("digest_len")
    except ReplaySafeReasoningPostureError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-21-rsp-hash-stability",
        "name": "gp06_rsp04_pinned_tuple_hash_stable_under_posture",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rsp_detail(errors),
    }
