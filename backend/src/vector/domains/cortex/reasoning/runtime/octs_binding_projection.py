"""RUNTIME-03 — bind TCRE reconstruction to OCTS traversal replay identity (fail-closed)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.reasoning.replay_chronology import (
    REASONING_REPLAY_PERMUTATION_PROFILE_ID,
    REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
    canonical_reasoning_replay_permutation_v1_json,
)

TCRE_OCTS_BINDING_SCHEMA_VERSION: Final[int] = 1

TRAVERSAL_BINDING_STATUS_BOUND: Final[str] = "traversal_replay_bound"
TRAVERSAL_BINDING_STATUS_UNBOUND: Final[str] = "traversal_replay_unbound"
TRAVERSAL_BINDING_STATUS_EPOCH_MISMATCH: Final[str] = "traversal_epoch_mismatch"
TRAVERSAL_BINDING_STATUS_CONTINUITY_UNVERIFIED: Final[str] = "traversal_continuity_unverified"

TRAVERSAL_BINDING_LEGALITY_CLASSES: Final[frozenset[str]] = frozenset(
    {
        TRAVERSAL_BINDING_STATUS_BOUND,
        TRAVERSAL_BINDING_STATUS_UNBOUND,
        TRAVERSAL_BINDING_STATUS_EPOCH_MISMATCH,
        TRAVERSAL_BINDING_STATUS_CONTINUITY_UNVERIFIED,
    }
)


class OctsBindingError(ValueError):
    """Fail-closed OCTS traversal binding for TCRE runtime."""


def _hop_receipt_digest_list(walk_payload: Mapping[str, Any]) -> list[str]:
    wr = walk_payload.get("walk_result") or {}
    hb = wr.get("hash_body") or {}
    hops = hb.get("hop_receipts")
    if not isinstance(hops, list):
        return []
    digests: list[str] = []
    for h in hops:
        if isinstance(h, Mapping):
            d = h.get("hop_receipt_digest") or h.get("receipt_digest")
            if isinstance(d, str) and d.strip():
                digests.append(d.strip())
    return sorted(digests)


def build_traversal_receipt_digest_v1(walk_payload: Mapping[str, Any]) -> str:
    """Deterministic digest over sorted hop receipt digests (structural traversal evidence)."""
    body = {"hop_receipt_digests": _hop_receipt_digest_list(walk_payload)}
    return hash_reasoning_canonical_json_sha256_v1(body)


def build_ingestion_replay_identity_v1(
    *,
    walk_result_hash: str,
    traversal_receipt_digest: str,
    tcre_policy_bundle_digest: str,
    reasoning_rule_pack_id: str,
    traversal_permutation_profile: str,
) -> str:
    body = {
        "walk_result_hash": walk_result_hash,
        "traversal_receipt_digest": traversal_receipt_digest,
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
        "reasoning_rule_pack_id": reasoning_rule_pack_id,
        "traversal_permutation_profile": traversal_permutation_profile,
    }
    return hash_reasoning_canonical_json_sha256_v1(body)


def build_chronology_legality_envelope_v1(
    chronology_rows: Sequence[Mapping[str, Any]],
) -> str:
    tuples = sorted(
        (
            str(r.get("materialization_id") or ""),
            str(r.get("chronology_legality_class") or ""),
        )
        for r in chronology_rows
    )
    return hash_reasoning_canonical_json_sha256_v1({"chronology_legality_tuples": tuples})


def resolve_octs_walk_payload_v1(
    tenant_id: uuid.UUID,
    *,
    octs_walk_id: str | None,
    session: Session | None = None,
) -> dict[str, Any] | None:
    if not octs_walk_id or not str(octs_walk_id).strip():
        return None
    from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1

    try:
        wid = uuid.UUID(str(octs_walk_id).strip())
    except ValueError:
        return None
    rec = resolve_octs_walk_store_v1(session).get(tenant_id, wid)
    if rec is None or rec.walk_payload is None:
        return None
    return dict(rec.walk_payload)


def build_octs_replay_identity_envelope_v1(
    *,
    tenant_id: uuid.UUID,
    scope: Mapping[str, Any],
    chronology_rows: Sequence[Mapping[str, Any]],
    tcre_policy_bundle_digest: str,
    reasoning_rule_pack_id: str,
    strict_binding: bool,
    session: Session | None = None,
) -> dict[str, Any]:
    """Derive OCTS replay identity envelope; fail closed when strict and evidence missing."""
    octs_walk_id = scope.get("octs_walk_id")
    expected_epoch = scope.get("traversal_epoch")
    expected_walk_hash = scope.get("expected_walk_result_hash")
    walk_payload = resolve_octs_walk_payload_v1(
        tenant_id,
        octs_walk_id=str(octs_walk_id or ""),
        session=session,
    )

    permutation = canonical_reasoning_replay_permutation_v1_json(
        ["materialization_id"],
        within_partition_reverse=False,
        shuffle_independent_partitions=False,
    )

    if walk_payload is None:
        if strict_binding:
            raise OctsBindingError("octs_strict_binding_requires_completed_walk")
        return {
            "schema_version": TCRE_OCTS_BINDING_SCHEMA_VERSION,
            "binding_legality_class": TRAVERSAL_BINDING_STATUS_UNBOUND,
            "walk_hash": REPLAY_PINNED_WALK_NO_INPUT_SENTINEL,
            "traversal_receipt_digest": "",
            "ingestion_replay_identity": "",
            "continuity_proof_ref": None,
            "traversal_epoch": None,
            "traversal_permutation_profile": REASONING_REPLAY_PERMUTATION_PROFILE_ID,
            "chronology_legality_envelope": build_chronology_legality_envelope_v1(chronology_rows),
            "octs_walk_id": str(octs_walk_id) if octs_walk_id else None,
        }

    wr = walk_payload.get("walk_result") or {}
    walk_hash = str(wr.get("walk_result_hash") or REPLAY_PINNED_WALK_NO_INPUT_SENTINEL)
    trav_digest = build_traversal_receipt_digest_v1(walk_payload)
    replay_id = build_ingestion_replay_identity_v1(
        walk_result_hash=walk_hash,
        traversal_receipt_digest=trav_digest,
        tcre_policy_bundle_digest=tcre_policy_bundle_digest,
        reasoning_rule_pack_id=reasoning_rule_pack_id,
        traversal_permutation_profile=REASONING_REPLAY_PERMUTATION_PROFILE_ID,
    )
    hb = wr.get("hash_body") or {}
    epoch = hb.get("traversal_epoch") or hb.get("walk_epoch")
    continuity_ref = hb.get("continuity_proof_ref") or scope.get("continuity_proof_ref")

    legality = TRAVERSAL_BINDING_STATUS_BOUND
    if expected_walk_hash and str(expected_walk_hash) != walk_hash:
        legality = TRAVERSAL_BINDING_STATUS_EPOCH_MISMATCH
    elif expected_epoch is not None and epoch is not None and str(expected_epoch) != str(epoch):
        legality = TRAVERSAL_BINDING_STATUS_EPOCH_MISMATCH
    elif continuity_ref is None and strict_binding:
        legality = TRAVERSAL_BINDING_STATUS_CONTINUITY_UNVERIFIED

    if strict_binding and legality != TRAVERSAL_BINDING_STATUS_BOUND:
        raise OctsBindingError(f"octs_binding_failed:{legality}")

    envelope = {
        "schema_version": TCRE_OCTS_BINDING_SCHEMA_VERSION,
        "binding_legality_class": legality,
        "walk_hash": walk_hash,
        "traversal_receipt_digest": trav_digest,
        "ingestion_replay_identity": replay_id,
        "continuity_proof_ref": str(continuity_ref) if continuity_ref else None,
        "traversal_epoch": str(epoch) if epoch is not None else None,
        "traversal_permutation_profile": REASONING_REPLAY_PERMUTATION_PROFILE_ID,
        "reasoning_replay_permutation_v1": permutation,
        "chronology_legality_envelope": build_chronology_legality_envelope_v1(chronology_rows),
        "octs_walk_id": str(octs_walk_id),
    }
    envelope["octs_binding_digest"] = hash_reasoning_canonical_json_sha256_v1(
        {k: v for k, v in envelope.items() if k != "octs_binding_digest"}
    )
    return envelope


def assert_replay_identity_stable_v1(
    prior: Mapping[str, Any],
    current: Mapping[str, Any],
) -> None:
    """Replay equivalence MUST fail when traversal replay identity drifts."""
    if prior.get("ingestion_replay_identity") != current.get("ingestion_replay_identity"):
        raise OctsBindingError("traversal_replay_identity_drift")
