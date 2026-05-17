"""Retrieval legality classes — fail-closed gate."""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

RETRIEVAL_LEGALITY_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "retrieval_replay_safe",
        "retrieval_degraded",
        "retrieval_partial",
        "retrieval_unverifiable",
        "retrieval_forbidden",
    }
)

RETRIEVAL_POLICY_BODY_V1: Final[dict[str, Any]] = {
    "schema_version": 1,
    "index_only_lawful_artifacts": True,
    "forbid_raw_exhaust_index": True,
    "forbid_unresolved_chronology": True,
    "forbid_replay_conflicted_identity": True,
    "require_degradation_visibility": True,
}


def retrieval_policy_digest_v1() -> str:
    return hash_reasoning_canonical_json_sha256_v1(RETRIEVAL_POLICY_BODY_V1)


class RetrievalLegalityError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = dict(detail or {})


def classify_retrieval_legality_v1(
    *,
    replay_identity_match: bool,
    chronology_legality_class: str,
    causal_legality_class: str,
    degradation_posture: str,
    continuity_posture: str,
    traversal_degraded: bool,
) -> str:
    if not replay_identity_match:
        return "retrieval_unverifiable"
    if chronology_legality_class in ("illegal", "unverifiable"):
        return "retrieval_unverifiable"
    if causal_legality_class in ("illegal", "unverifiable"):
        return "retrieval_unverifiable"
    if continuity_posture in ("replay_unsafe", "unresolved"):
        return "retrieval_unverifiable"
    if traversal_degraded or degradation_posture == "degraded":
        return "retrieval_degraded"
    if degradation_posture == "partial" or continuity_posture == "partial":
        return "retrieval_partial"
    return "retrieval_replay_safe"


def assert_retrieval_lawful_v1(
    *,
    legality_class: str,
    replay_posture: str,
) -> None:
    assert_retrieval_query_lawful_v1(
        legality_class=legality_class,
        replay_posture=replay_posture,
        intent="inspect",
        execution_partition="authoritative",
    )


def assert_retrieval_query_lawful_v1(
    *,
    legality_class: str,
    replay_posture: str,
    intent: str,
    execution_partition: str = "authoritative",
) -> None:
    if legality_class not in RETRIEVAL_LEGALITY_CLASSES_V1:
        raise RetrievalLegalityError("unknown_retrieval_legality_class")
    if legality_class == "retrieval_forbidden":
        raise RetrievalLegalityError(
            "retrieval_forbidden",
            detail={"legality_class": legality_class, "replay_posture": replay_posture},
        )
    if legality_class == "retrieval_unverifiable" and intent != "audit":
        raise RetrievalLegalityError(
            "retrieval_fail_closed",
            detail={"legality_class": legality_class, "replay_posture": replay_posture},
        )
    if (
        execution_partition == "authoritative"
        and legality_class == "retrieval_partial"
        and intent != "audit"
    ):
        raise RetrievalLegalityError(
            "retrieval_partial_requires_audit_intent",
            detail={"legality_class": legality_class, "intent": intent},
        )
