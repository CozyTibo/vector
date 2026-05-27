"""Phase 01 Step 15 — live-lane logical identity + revision key derivation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

_ENVELOPE_EXCLUDE_KEYS = {
    "schema_version",
    "connector_type",
    "connector_instance_id",
    "source_object_type",
    "source_object_id",
    "ingestion_version",
    "cortex_replay_metadata",
    # Ingestion transport wrappers (not source truth).
    "paging",
    "connectivity",
}

_REVISION_TOKEN_PRIORITY = (
    "updatedAt",
    "updated_at",
    "updated",
    "last_edited_time",
    "lastEditedAt",
    "version",
    "etag",
    "sha",
    "ts",
)


def _normalize_for_hash(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize_for_hash(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [_normalize_for_hash(v) for v in value]
    if isinstance(value, str):
        return value.strip()
    return value


def canonical_source_payload_segment(body: dict[str, Any]) -> dict[str, Any]:
    """Strip envelope/transport keys; keep deterministic provider payload segment."""
    return {k: body[k] for k in sorted(body) if k not in _ENVELOPE_EXCLUDE_KEYS}


def canonical_payload_hash(body: dict[str, Any]) -> str:
    """Deterministic hash over normalized source payload segment."""
    segment = canonical_source_payload_segment(body)
    normalized = _normalize_for_hash(segment)
    dumped = json.dumps(normalized, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(dumped.encode()).hexdigest()


def _find_revision_token(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in _REVISION_TOKEN_PRIORITY:
            val = value.get(key)
            if isinstance(val, (str, int, float)) and str(val).strip():
                return str(val).strip()
        for k in sorted(value):
            found = _find_revision_token(value[k])
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_revision_token(item)
            if found is not None:
                return found
    return None


def derive_source_identity_key(*, connector: str, resource_type: str, external_id: str) -> str:
    base = f"{connector}:{resource_type}:{external_id.strip()}"
    if len(base) <= 255:
        return base
    digest = hashlib.sha256(base.encode()).hexdigest()
    return f"{connector}:{resource_type}:sha256:{digest}"[:255]


def _extraction_version(body: dict[str, Any]) -> int | None:
    ing = body.get("ingestion_version")
    if not isinstance(ing, dict):
        return None
    raw = ing.get("extraction")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def derive_source_revision_key(body: dict[str, Any]) -> str:
    segment = canonical_source_payload_segment(body)
    token = _find_revision_token(segment)
    if token:
        norm = token[:96]
        return f"provider:{norm}"[:128]
    extraction = _extraction_version(body)
    digest = canonical_payload_hash(body)
    if extraction is not None and extraction > 0:
        return f"extract:{extraction}:hash:{digest}"[:128]
    return f"hash:{digest}"[:128]


def derive_logical_idempotency_key(*, source_identity_key: str, source_revision_key: str) -> str:
    raw = f"{source_identity_key}|{source_revision_key}"
    return hashlib.sha256(raw.encode()).hexdigest()
