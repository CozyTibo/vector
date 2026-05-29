"""Shared mapper helpers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from vector.domains.cortex.canon.mapper_types import CanonMapResult, CanonSourceRef
from vector.domains.cortex.ingestion.live_idempotency import derive_source_identity_key
from vector.domains.cortex.ingestion.temporal_ordering import derive_provider_event_timestamp


def entity_key_for(
    *,
    tenant_id: uuid.UUID,
    connector: str,
    resource_type: str,
    external_id: str,
) -> str:
    base = derive_source_identity_key(
        connector=connector,
        resource_type=resource_type,
        external_id=external_id,
    )
    return f"{tenant_id}:{base}"[:512]


def source_ref(
    *,
    raw_id: int,
    connector: str,
    resource_type: str,
    external_id: str,
    source_identity_key: str,
    source_revision_key: str,
    payload_body: dict[str, Any],
    fetched_at_iso: str,
) -> CanonSourceRef:
    ts = derive_provider_event_timestamp(payload_body)
    observed = ts.isoformat() if ts is not None else fetched_at_iso
    return CanonSourceRef(
        raw_id=raw_id,
        connector=connector,
        resource_type=resource_type,
        external_id=external_id,
        source_identity_key=source_identity_key,
        source_revision_key=source_revision_key,
        observed_at_iso=observed,
    )


def skip_result(
    *,
    raw_id: int,
    connector: str,
    resource_type: str,
    external_id: str,
    source_identity_key: str,
    source_revision_key: str,
    payload_body: dict[str, Any],
    fetched_at_iso: str,
    reason: str,
) -> CanonMapResult:
    return CanonMapResult(
        draft=None,
        source=source_ref(
            raw_id=raw_id,
            connector=connector,
            resource_type=resource_type,
            external_id=external_id,
            source_identity_key=source_identity_key,
            source_revision_key=source_revision_key,
            payload_body=payload_body,
            fetched_at_iso=fetched_at_iso,
        ),
        skip_reason=reason,
    )


def _first_str(*values: object) -> str | None:
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def notion_plain_text(value: object) -> str | None:
    """Extract display text from a Notion string or rich_text / title array."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            plain = item.get("plain_text")
            if isinstance(plain, str) and plain.strip():
                parts.append(plain.strip())
        if parts:
            return " ".join(parts)
    return None


def label_from_payload(payload_body: dict[str, Any], *keys: str) -> str:
    for key in keys:
        segment = payload_body.get(key)
        if isinstance(segment, dict):
            for sub in ("title", "name", "login", "identifier", "text", "id"):
                val = segment.get(sub)
                rich = notion_plain_text(val)
                if rich:
                    return rich[:512]
                if isinstance(val, str) and val.strip():
                    return val.strip()[:512]
        if isinstance(segment, str) and segment.strip():
            return segment.strip()[:512]
    return payload_body.get("source_object_id", "unknown")[:512]
