"""Phase 06 P06-09 — replay chronology semantics (pinned tuple + permutation + bridge).

Normative:
``DOCS/cortex/reasoning/replay-aware-reasoning-law.md``,
``DOCS/cortex/reasoning/replay-equivalence-reasoning-spec.md`` §3,
``DOCS/cortex/reasoning/chronology-replay-legality-state-machine.md`` (projection inputs).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.temporal_anchor_resolution import hash_reasoning_receipt_canonical_v1

PHASE06_REPLAY_CHRONOLOGY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

REASONING_REPLAY_PERMUTATION_PROFILE_ID: Final[str] = "reasoning_replay_permutation_v1"

REPLAY_PINNED_WALK_NO_INPUT_SENTINEL: Final[str] = "__NO_WALK_INPUT__"

REASONING_REPLAY_RECEIPT_TYPE: Final[str] = "reasoning_replay_receipt"


class ReplayChronologyError(ValueError):
    """Fail-closed replay permutation / pinned tuple / chronology bridge."""


def _canonical_json(obj: Mapping[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_reasoning_replay_permutation_v1_json(
    partition_keys: Sequence[str],
    *,
    within_partition_reverse: bool = False,
    shuffle_independent_partitions: bool = True,
) -> str:
    """§3 ``replay-equivalence-reasoning-spec`` — canonical permutation id string (sorted keys)."""
    keys = [str(k) for k in partition_keys]
    if any(not x.strip() for x in keys):
        raise ReplayChronologyError("partition_keys must be non-empty strings")
    sorted_keys = sorted(keys)
    body: dict[str, Any] = {
        "partition_keys_sorted": sorted_keys,
        "profile_id": REASONING_REPLAY_PERMUTATION_PROFILE_ID,
        "shuffle_independent_partitions": bool(shuffle_independent_partitions),
        "within_partition_reverse": bool(within_partition_reverse),
    }
    return _canonical_json(body)


def validate_reasoning_replay_permutation_v1_json(permutation_json: str) -> dict[str, Any]:
    """Parse and validate a frozen ``reasoning_replay_permutation_v1`` canonical JSON string."""
    if not isinstance(permutation_json, str) or not permutation_json.strip():
        raise ReplayChronologyError("permutation_json must be non-empty")
    try:
        obj = json.loads(permutation_json)
    except json.JSONDecodeError as exc:
        raise ReplayChronologyError(f"invalid permutation JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ReplayChronologyError("permutation JSON must be an object")
    pid = obj.get("profile_id")
    if pid != REASONING_REPLAY_PERMUTATION_PROFILE_ID:
        raise ReplayChronologyError(f"profile_id must be {REASONING_REPLAY_PERMUTATION_PROFILE_ID!r}")
    pks = obj.get("partition_keys_sorted")
    if not isinstance(pks, list) or not all(isinstance(x, str) for x in pks):
        raise ReplayChronologyError("partition_keys_sorted must be a list of strings")
    if pks != sorted(pks):
        raise ReplayChronologyError("partition_keys_sorted must be sorted ascending")
    allowed = {
        "partition_keys_sorted",
        "profile_id",
        "shuffle_independent_partitions",
        "within_partition_reverse",
    }
    if frozenset(obj.keys()) != allowed:
        raise ReplayChronologyError("permutation object must contain only the v1 frozen keys")
    for flag in ("within_partition_reverse", "shuffle_independent_partitions"):
        if not isinstance(obj[flag], bool):
            raise ReplayChronologyError(f"{flag} must be bool")
    if _canonical_json(obj) != permutation_json:
        raise ReplayChronologyError("permutation_json is not in canonical sorted-key form")
    return obj


def validate_pinned_replay_chronology_tuple_v1(
    *,
    raw_evidence_bundle_digest: str,
    reasoning_rule_pack_id: str,
    tcre_policy_bundle_digest: str,
    reasoning_replay_permutation_v1: str,
    walk_result_hash: str,
) -> dict[str, Any]:
    """``replay-aware-reasoning-law`` §1 — pinned tuple (A–E) for deterministic replay."""
    if not isinstance(raw_evidence_bundle_digest, str) or not raw_evidence_bundle_digest.strip():
        raise ReplayChronologyError("raw_evidence_bundle_digest (A) must be non-empty")
    if not isinstance(reasoning_rule_pack_id, str) or not reasoning_rule_pack_id.strip():
        raise ReplayChronologyError("reasoning_rule_pack_id (B) must be non-empty")
    if not isinstance(tcre_policy_bundle_digest, str) or not tcre_policy_bundle_digest.strip():
        raise ReplayChronologyError("tcre_policy_bundle_digest (C) must be non-empty")
    validate_reasoning_replay_permutation_v1_json(reasoning_replay_permutation_v1)
    if not isinstance(walk_result_hash, str) or not walk_result_hash.strip():
        raise ReplayChronologyError("walk_result_hash (E) must be non-empty")
    return {
        "raw_evidence_bundle_digest": raw_evidence_bundle_digest.strip(),
        "reasoning_rule_pack_id": reasoning_rule_pack_id.strip(),
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest.strip(),
        "reasoning_replay_permutation_v1": reasoning_replay_permutation_v1,
        "walk_result_hash": walk_result_hash.strip(),
    }


def hash_pinned_replay_chronology_tuple_v1(pinned: Mapping[str, Any]) -> str:
    """Deterministic digest of the pinned tuple (canonical JSON, sorted keys)."""
    expected = frozenset(
        {
            "raw_evidence_bundle_digest",
            "reasoning_rule_pack_id",
            "tcre_policy_bundle_digest",
            "reasoning_replay_permutation_v1",
            "walk_result_hash",
        }
    )
    if frozenset(pinned.keys()) != expected:
        raise ReplayChronologyError("pinned tuple must contain exactly keys A–E")
    body = validate_pinned_replay_chronology_tuple_v1(
        raw_evidence_bundle_digest=str(pinned["raw_evidence_bundle_digest"]),
        reasoning_rule_pack_id=str(pinned["reasoning_rule_pack_id"]),
        tcre_policy_bundle_digest=str(pinned["tcre_policy_bundle_digest"]),
        reasoning_replay_permutation_v1=str(pinned["reasoning_replay_permutation_v1"]),
        walk_result_hash=str(pinned["walk_result_hash"]),
    )
    return hash_reasoning_receipt_canonical_v1(body)


def validate_chronology_snapshot_matches_pinned_replay_tuple_v1(
    *,
    pinned_tuple: Mapping[str, Any],
    chronology_projection_snapshot: Mapping[str, Any],
) -> None:
    """Tuple bridge — policy digest + rule pack id used for projection must match pinned (B)(C)."""
    pinned = validate_pinned_replay_chronology_tuple_v1(
        raw_evidence_bundle_digest=str(pinned_tuple["raw_evidence_bundle_digest"]),
        reasoning_rule_pack_id=str(pinned_tuple["reasoning_rule_pack_id"]),
        tcre_policy_bundle_digest=str(pinned_tuple["tcre_policy_bundle_digest"]),
        reasoning_replay_permutation_v1=str(pinned_tuple["reasoning_replay_permutation_v1"]),
        walk_result_hash=str(pinned_tuple["walk_result_hash"]),
    )
    snap_digest = chronology_projection_snapshot.get("tcre_policy_bundle_digest")
    if snap_digest is not None:
        if str(snap_digest).strip() != pinned["tcre_policy_bundle_digest"]:
            raise ReplayChronologyError(
                "chronology_projection_snapshot.tcre_policy_bundle_digest must equal pinned (C)"
            )
    snap_pack = chronology_projection_snapshot.get("reasoning_rule_pack_id")
    if snap_pack is not None:
        if str(snap_pack).strip() != pinned["reasoning_rule_pack_id"]:
            raise ReplayChronologyError(
                "chronology_projection_snapshot.reasoning_rule_pack_id must equal pinned (B)"
            )


def reasoning_replay_receipt_body_v1(
    *,
    pinned_tuple: Mapping[str, Any],
    walk_result_hash: str | None = None,
    index_content_hash: str | None = None,
) -> dict[str, Any]:
    """Minimal ``reasoning_replay_receipt`` body (``reasoning-receipts-and-proof-artifacts.md`` §1)."""
    p = validate_pinned_replay_chronology_tuple_v1(
        raw_evidence_bundle_digest=str(pinned_tuple["raw_evidence_bundle_digest"]),
        reasoning_rule_pack_id=str(pinned_tuple["reasoning_rule_pack_id"]),
        tcre_policy_bundle_digest=str(pinned_tuple["tcre_policy_bundle_digest"]),
        reasoning_replay_permutation_v1=str(pinned_tuple["reasoning_replay_permutation_v1"]),
        walk_result_hash=str(pinned_tuple["walk_result_hash"]),
    )
    wh = walk_result_hash if walk_result_hash is not None else p["walk_result_hash"]
    body: dict[str, Any] = {
        "receipt_type": REASONING_REPLAY_RECEIPT_TYPE,
        "phase06_replay_chronology_runtime_schema_version": PHASE06_REPLAY_CHRONOLOGY_RUNTIME_SCHEMA_VERSION,
        "pinned_replay_chronology_tuple": p,
        "walk_result_hash": str(wh).strip(),
    }
    if index_content_hash is not None:
        if not isinstance(index_content_hash, str) or not index_content_hash.strip():
            raise ReplayChronologyError("index_content_hash must be non-empty when provided")
        body["index_content_hash"] = index_content_hash.strip()
    return body


def verify_gp06_rep01_permutation_canonical_static() -> dict[str, Any]:
    """Static: canonical permutation JSON matches §3 example shape (sorted keys)."""
    errors: list[str] = []
    expected_keys = (
        "partition_keys_sorted",
        "profile_id",
        "shuffle_independent_partitions",
        "within_partition_reverse",
    )
    js = canonical_reasoning_replay_permutation_v1_json(
        ["github:connA", "slack:connB"],
        within_partition_reverse=False,
        shuffle_independent_partitions=True,
    )
    try:
        obj = json.loads(js)
    except json.JSONDecodeError as exc:
        errors.append(f"json_parse:{exc}")
    else:
        if tuple(sorted(obj)) != expected_keys:
            errors.append(f"key_order_mismatch:{sorted(obj)}")
        if obj.get("profile_id") != REASONING_REPLAY_PERMUTATION_PROFILE_ID:
            errors.append("profile_id")
        if obj.get("partition_keys_sorted") != ["github:connA", "slack:connB"]:
            errors.append("partition_sort")
    try:
        validate_reasoning_replay_permutation_v1_json(js)
    except ReplayChronologyError as exc:
        errors.append(f"validate_permutation:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-09-rep-permutation",
        "name": "reasoning_replay_permutation_v1_canonical",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_replay_chronology_runtime_schema_version": (
                PHASE06_REPLAY_CHRONOLOGY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_rep02_pinned_tuple_hash_static() -> dict[str, Any]:
    """Static: pinned tuple validates and digest is stable 64-hex."""
    errors: list[str] = []
    try:
        perm = canonical_reasoning_replay_permutation_v1_json(["p1"])
        pinned = validate_pinned_replay_chronology_tuple_v1(
            raw_evidence_bundle_digest="sha256:" + "a" * 64,
            reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
            tcre_policy_bundle_digest="d48f77eb363cc2828b7af5351365d3e96dc5e1b4464c5fa1b6a5d6c56590f470",
            reasoning_replay_permutation_v1=perm,
            walk_result_hash=REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
        )
        d = hash_pinned_replay_chronology_tuple_v1(pinned)
        if len(d) != 64:
            errors.append("digest_len")
    except ReplayChronologyError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-09-rep-pinned-tuple",
        "name": "pinned_replay_chronology_tuple_digest",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_replay_chronology_runtime_schema_version": (
                PHASE06_REPLAY_CHRONOLOGY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
