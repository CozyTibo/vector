"""Lineage receipt digests (hash-stable ids)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)


def lineage_receipt_digest_v1(body: Mapping[str, Any]) -> str:
    return hash_reasoning_canonical_json_sha256_v1(dict(body))
