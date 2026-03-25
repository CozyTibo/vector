"""Payload integrity + idempotency helpers for ingestion envelopes."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any


def canonical_json_bytes(obj: Any) -> bytes:
    """Deterministic JSON for hashing (sorted keys, no whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def canonical_payload_hash(obj: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def idempotency_key(
    *,
    run_id: uuid.UUID,
    resource_type: str,
    external_id: str,
    api_endpoint: str,
    query_params: dict[str, Any],
) -> str:
    """Stable key for (run, resource, request); retries should not double-insert."""
    qp = canonical_json_bytes(query_params).decode("ascii")
    raw = f"{run_id}:{resource_type}:{external_id}:{api_endpoint}:{qp}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
