"""Lightweight org-shaped execution primitives (Phase 3.5) — sparse envelopes only.

These are **not** workflow engines or AI narratives. Each primitive must cite evidence (raw ids)
and use deterministic keys derived from evidence fields.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal, TypedDict

EXECUTION_PRIMITIVE_SCHEMA_VERSION: int = 1


class ExecutionPrimitiveKind(StrEnum):
    WORK_EPISODE = "work_episode"
    DELIVERY_ATTEMPT = "delivery_attempt"
    REVIEW_CYCLE = "review_cycle"
    ESCALATION_CHAIN = "escalation_chain"
    OWNERSHIP_WINDOW = "ownership_window"
    COORDINATION_BURST = "coordination_burst"
    BLOCKING_RELATIONSHIP = "blocking_relationship"
    DECISION_REFERENCE = "decision_reference"


PrimitiveStatus = Literal["open", "closed", "unknown"]


class ExecutionPrimitiveEnvelope(TypedDict, total=False):
    execution_primitive_schema_version: int
    kind: str
    primitive_key: str
    """Deterministic hash key from sorted evidence tuple (see ``derive_primitive_key``)."""
    status: PrimitiveStatus
    evidence_raw_record_ids: list[int]
    """Non-empty for persisted primitives in later phases; may be empty in planning-only payloads."""
    normalized_references: list[dict[str, Any]]
    """Optional ``NormalizedReference`` dicts anchoring the primitive."""
    opened_at_iso: str | None
    closed_at_iso: str | None
    bundle_id: str
    tenant_id: str
    notes: str | None
    """Operator-only short deterministic label; no NL inference."""


def derive_primitive_key(
    *,
    kind: ExecutionPrimitiveKind,
    evidence_parts: dict[str, Any],
) -> str:
    """Stable key: SHA-256 over canonical JSON of kind + sorted evidence parts."""
    payload = {"kind": kind.value, "evidence": {k: evidence_parts[k] for k in sorted(evidence_parts.keys())}}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def build_execution_primitive_envelope(
    *,
    kind: ExecutionPrimitiveKind,
    evidence_parts: dict[str, Any],
    evidence_raw_record_ids: list[int],
    bundle_id: str,
    tenant_id: str,
    normalized_references: list[dict[str, Any]] | None = None,
    status: PrimitiveStatus = "unknown",
    opened_at_iso: str | None = None,
    closed_at_iso: str | None = None,
    notes: str | None = None,
) -> ExecutionPrimitiveEnvelope:
    return {
        "execution_primitive_schema_version": EXECUTION_PRIMITIVE_SCHEMA_VERSION,
        "kind": kind.value,
        "primitive_key": derive_primitive_key(kind=kind, evidence_parts=evidence_parts),
        "status": status,
        "evidence_raw_record_ids": list(evidence_raw_record_ids),
        "normalized_references": list(normalized_references or []),
        "opened_at_iso": opened_at_iso,
        "closed_at_iso": closed_at_iso,
        "bundle_id": bundle_id,
        "tenant_id": tenant_id,
        "notes": notes,
    }
