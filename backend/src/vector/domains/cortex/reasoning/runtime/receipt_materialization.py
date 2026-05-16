"""Persistable receipt / degradation / equivalence bodies for RUNTIME-01."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from vector.domains.cortex.reasoning.chronology_degradation_propagation import CD_CHRON
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    REASONING_AMBIGUITY_RECEIPT_TYPE,
    REASONING_CANON_VERSION_V1,
    REASONING_EQUIVALENCE_RECEIPT_TYPE,
    hash_reasoning_canonical_json_sha256_v1,
)


def build_degradation_receipt_v1(
    chronology_rows: Sequence[Mapping[str, Any]],
    *,
    tcre_policy_bundle_digest: str,
) -> dict[str, Any] | None:
    cd_codes: list[str] = []
    for row in chronology_rows:
        if row.get("chronology_legality_class") == "chronology_degraded":
            cd_codes.append(CD_CHRON)
    if not cd_codes:
        return None
    body = {
        "cd_codes": sorted(set(cd_codes)),
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
        "source": "runtime01_chronology_projection",
    }
    return {
        "receipt_body": body,
        "receipt_digest": hash_reasoning_canonical_json_sha256_v1(body),
    }


def build_equivalence_receipt_v1(
    *,
    double_run_digest_a: str,
    double_run_digest_b: str,
) -> dict[str, Any]:
    body = {
        "receipt_type": REASONING_EQUIVALENCE_RECEIPT_TYPE,
        "reasoning_canon_version_v1": REASONING_CANON_VERSION_V1,
        "double_run_digest_a": double_run_digest_a,
        "double_run_digest_b": double_run_digest_b,
    }
    return {
        "receipt_body": body,
        "receipt_digest": hash_reasoning_canonical_json_sha256_v1(body),
    }


def build_runtime_ambiguity_stub_receipt_v1(
    *,
    ambiguity_class_id: str,
    blocked_derivation_rules_hash: str,
) -> dict[str, Any]:
    body = {
        "receipt_type": REASONING_AMBIGUITY_RECEIPT_TYPE,
        "reasoning_canon_version_v1": REASONING_CANON_VERSION_V1,
        "ambiguity_class_id": ambiguity_class_id,
        "blocked_derivation_rules_hash": blocked_derivation_rules_hash,
    }
    return {
        "receipt_body": body,
        "receipt_digest": hash_reasoning_canonical_json_sha256_v1(body),
    }


def aggregate_artifact_digest_v1(digests: Sequence[str]) -> str:
  rows = [{"digest": d} for d in sorted(digests)]
  return hash_reasoning_canonical_json_sha256_v1({"rows": rows})
