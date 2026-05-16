"""Retrieval lookup id derivation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)


def derive_retrieval_lookup_id_v1(
    *,
    index_kind: str,
    index_key: str,
    replay_identity: str,
) -> str:
    return hash_reasoning_canonical_json_sha256_v1(
        {"index_kind": index_kind, "index_key": index_key, "replay_identity": replay_identity}
    )[:32]
