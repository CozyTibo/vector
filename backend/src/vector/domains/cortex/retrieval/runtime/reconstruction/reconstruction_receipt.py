"""Structural reconstruction receipts for operator audit."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)


def build_reconstruction_receipt_v1(
    *,
    scope: Mapping[str, Any],
    artifact_refs_resolved: Sequence[Mapping[str, Any]],
    hit_count: int,
    omission_count: int,
) -> dict[str, Any]:
    body = {
        "scope": dict(scope),
        "artifact_refs_resolved": [dict(r) for r in artifact_refs_resolved],
        "hit_count": int(hit_count),
        "omission_count": int(omission_count),
    }
    digest = hash_reasoning_canonical_json_sha256_v1(body)
    return {
        "schema_version": 1,
        "reconstruction_receipt_digest": digest,
        "body": body,
    }
