"""Retrieval lookup id derivation (content-addressed)."""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

RETRIEVAL_INDEX_CANON_VERSION_V1: Final[str] = "RETRIEVAL-INDEX-1"


def format_retrieval_lookup_id_v1(digest_hex: str) -> str:
    """Format ``sha256:`` + 64 lowercase hex (**RET-ADDR-01**)."""
    raw = str(digest_hex).strip().lower()
    if raw.startswith("sha256:") and len(raw) != 71:
        return raw
    if raw.startswith("sha256:"):
        hex_part = raw[7:]
    else:
        hex_part = raw
    if len(hex_part) != 64:
        raise ValueError("retrieval_lookup_id requires 64-char sha256 hex digest")
    return f"sha256:{hex_part}"


def derive_retrieval_lookup_id_v1(
    *,
    index_kind: str,
    index_key: str,
    replay_identity: str,
) -> str:
    """Derive index-row ``retrieval_lookup_id`` (legacy index canon)."""
    body: dict[str, Any] = {
        "canon_version": RETRIEVAL_INDEX_CANON_VERSION_V1,
        "index_kind": index_kind,
        "index_key": index_key,
        "replay_identity": replay_identity,
    }
    return format_retrieval_lookup_id_v1(hash_reasoning_canonical_json_sha256_v1(body))
