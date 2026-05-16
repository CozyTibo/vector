"""Phase 06 P06-15 — deterministic causal chains (``causal_chain_id`` + policy digest law).

Normative:
``DOCS/cortex/reasoning/deterministic-causal-chain-spec.md`` §1,
``DOCS/cortex/reasoning/tcre-causal-edge-registry-v1.md`` (digest participation),
``DOCS/cortex/reasoning/reasoning-policy-pack-v1.md`` (``tcre_policy_bundle_digest``).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.causal_interval_closure import (
    CausalIntervalClosureError,
    canonical_sorted_tcre_causal_edge_ids_v1,
)

PHASE06_DETERMINISTIC_CAUSAL_CHAIN_RUNTIME_SCHEMA_VERSION: Final[int] = 1

_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[a-f0-9]{64}$")


class DeterministicCausalChainError(ValueError):
    """Fail-closed deterministic ``causal_chain_id`` construction / validation."""


def validate_tcre_policy_bundle_digest_shape_v1(digest: str) -> None:
    """``reasoning-policy-pack-v1.md`` — bundle digest is lowercase **sha256** hex (64 chars)."""
    if not isinstance(digest, str) or not digest.strip():
        raise DeterministicCausalChainError("tcre_policy_bundle_digest must be a non-empty string")
    s = digest.strip()
    if s != s.lower():
        raise DeterministicCausalChainError("tcre_policy_bundle_digest must use lowercase a-f hex digits")
    if not _SHA256_HEX_RE.match(s):
        raise DeterministicCausalChainError(
            "tcre_policy_bundle_digest must be 64-char lowercase hex sha256"
        )


def causal_chain_id_canonical_body_v1(
    *,
    tcre_causal_edge_ids: Sequence[str],
    reasoning_rule_pack_id: str,
    tcre_policy_bundle_digest: str,
    tenant_id: str,
) -> dict[str, Any]:
    """§1 — canonical JSON object inputs (sorted keys applied at serialize time)."""
    if not isinstance(reasoning_rule_pack_id, str) or not reasoning_rule_pack_id.strip():
        raise DeterministicCausalChainError("reasoning_rule_pack_id must be a non-empty string")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise DeterministicCausalChainError("tenant_id must be a non-empty string")
    validate_tcre_policy_bundle_digest_shape_v1(tcre_policy_bundle_digest)
    try:
        sorted_ids = canonical_sorted_tcre_causal_edge_ids_v1(list(tcre_causal_edge_ids))
    except CausalIntervalClosureError as exc:
        raise DeterministicCausalChainError(str(exc)) from exc
    s_digest = tcre_policy_bundle_digest.strip()
    fields = {
        "reasoning_rule_pack_id": reasoning_rule_pack_id.strip(),
        "tenant_id": tenant_id.strip(),
        "tcre_causal_edge_ids": sorted_ids,
        "tcre_policy_bundle_digest": s_digest,
    }
    return {k: fields[k] for k in sorted(fields)}


def hash_causal_chain_id_v1(
    *,
    tcre_causal_edge_ids: Sequence[str],
    reasoning_rule_pack_id: str,
    tcre_policy_bundle_digest: str,
    tenant_id: str,
) -> str:
    """§1 — ``causal_chain_id`` = **sha256** hex over sorted-keys canonical JSON of the law fields."""
    body = causal_chain_id_canonical_body_v1(
        tcre_causal_edge_ids=tcre_causal_edge_ids,
        reasoning_rule_pack_id=reasoning_rule_pack_id,
        tcre_policy_bundle_digest=tcre_policy_bundle_digest,
        tenant_id=tenant_id,
    )
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_causal_chain_id_v1(
    *,
    causal_chain_id: str,
    tcre_causal_edge_ids: Sequence[str],
    reasoning_rule_pack_id: str,
    tcre_policy_bundle_digest: str,
    tenant_id: str,
) -> None:
    """Fail closed when recomputed id does not match the supplied ``causal_chain_id``."""
    if not isinstance(causal_chain_id, str) or not causal_chain_id.strip():
        raise DeterministicCausalChainError("causal_chain_id must be a non-empty string")
    got = hash_causal_chain_id_v1(
        tcre_causal_edge_ids=tcre_causal_edge_ids,
        reasoning_rule_pack_id=reasoning_rule_pack_id,
        tcre_policy_bundle_digest=tcre_policy_bundle_digest,
        tenant_id=tenant_id,
    )
    if got != causal_chain_id.strip().lower():
        raise DeterministicCausalChainError(
            f"causal_chain_id mismatch: expected {got}, got {causal_chain_id!r}"
        )


def verify_gp06_dcc01_causal_chain_id_permutation_invariant_static() -> dict[str, Any]:
    """Static — unsorted input permutations yield the same ``causal_chain_id`` (lex canonicalization)."""
    errors: list[str] = []
    digest = "a" * 64
    try:
        a = hash_causal_chain_id_v1(
            tcre_causal_edge_ids=["edge_z", "edge_a"],
            reasoning_rule_pack_id="pack-1",
            tcre_policy_bundle_digest=digest,
            tenant_id="t1",
        )
        b = hash_causal_chain_id_v1(
            tcre_causal_edge_ids=["edge_a", "edge_z"],
            reasoning_rule_pack_id="pack-1",
            tcre_policy_bundle_digest=digest,
            tenant_id="t1",
        )
        if a != b:
            errors.append("permutation_invariant_failed")
    except DeterministicCausalChainError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-15-dcc-permutation",
        "name": "gp06_dcc01_causal_chain_id_permutation_invariant",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_deterministic_causal_chain_runtime_schema_version": (
                PHASE06_DETERMINISTIC_CAUSAL_CHAIN_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_dcc02_policy_digest_participates_static() -> dict[str, Any]:
    """Static — changing ``tcre_policy_bundle_digest`` changes ``causal_chain_id`` (**CHRON‑POL‑1** law)."""
    errors: list[str] = []
    d1 = "a" * 64
    d2 = "b" * 64
    try:
        h1 = hash_causal_chain_id_v1(
            tcre_causal_edge_ids=["e1"],
            reasoning_rule_pack_id="p",
            tcre_policy_bundle_digest=d1,
            tenant_id="t",
        )
        h2 = hash_causal_chain_id_v1(
            tcre_causal_edge_ids=["e1"],
            reasoning_rule_pack_id="p",
            tcre_policy_bundle_digest=d2,
            tenant_id="t",
        )
        if h1 == h2:
            errors.append("digest_change_did_not_change_chain_id")
    except DeterministicCausalChainError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-15-dcc-digest",
        "name": "gp06_dcc02_policy_digest_participates",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_deterministic_causal_chain_runtime_schema_version": (
                PHASE06_DETERMINISTIC_CAUSAL_CHAIN_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_dcc03_canonical_body_sorted_keys_static() -> dict[str, Any]:
    """Static — JSON serialization is sorted-key canonical and round-trips."""
    errors: list[str] = []
    try:
        body = causal_chain_id_canonical_body_v1(
            tcre_causal_edge_ids=["x"],
            reasoning_rule_pack_id="rp",
            tcre_policy_bundle_digest="c" * 64,
            tenant_id="tenant",
        )
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if json.loads(payload) != body:
            errors.append("json_roundtrip_mismatch")
        keys = list(body.keys())
        if keys != sorted(keys):
            errors.append("body_keys_not_sorted_in_mapping")
    except DeterministicCausalChainError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-15-dcc-canonical-json",
        "name": "gp06_dcc03_canonical_body_sorted_keys",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_deterministic_causal_chain_runtime_schema_version": (
                PHASE06_DETERMINISTIC_CAUSAL_CHAIN_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
