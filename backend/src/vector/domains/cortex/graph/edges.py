"""Edge draft produced by extractors."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class EdgeDraft:
    relationship_kind: str
    from_entity_id: uuid.UUID
    to_entity_id: uuid.UUID
    extractor_rule: str
    evidence_kind: str
    evidence_ref: str
    confidence: str = "certain"
    evidence_snapshot: dict[str, Any] | None = None
    source_raw_id: int | None = None
    source_canon_source_id: uuid.UUID | None = None
    observed_at: datetime | None = None


@dataclass(frozen=True)
class UnresolvedRefDraft:
    reference_kind: str
    reference_text: str
    extractor_rule: str
    evidence_snapshot: dict[str, Any] = field(default_factory=dict)
