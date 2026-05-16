"""Traversal epoch derivation (deterministic, replay-stable)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)


def derive_traversal_epoch_v1(
    *,
    walk_policy: Mapping[str, Any],
    temporal_anchor: Mapping[str, Any] | None,
    engine_build_ref: str,
) -> str:
    body = {
        "walk_policy": dict(walk_policy or {}),
        "temporal_anchor": dict(temporal_anchor or {}),
        "engine_build_ref": engine_build_ref,
    }
    return hash_reasoning_canonical_json_sha256_v1(body)[:32]
