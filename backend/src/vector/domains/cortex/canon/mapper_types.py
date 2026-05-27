"""Canon mapper contracts — raw row to normalized entity draft."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class CanonSourceRef:
    raw_id: int
    connector: str
    resource_type: str
    external_id: str
    source_identity_key: str
    source_revision_key: str
    observed_at_iso: str


@dataclass
class CanonEntityDraft:
    entity_type: str
    entity_key: str
    display_label: str
    connector: str
    connection_id: uuid.UUID
    attrs_json: dict[str, Any] = field(default_factory=dict)
    author_entity_id: uuid.UUID | None = None
    conversation_entity_id: uuid.UUID | None = None
    parent_message_entity_id: uuid.UUID | None = None
    repository_entity_id: uuid.UUID | None = None
    assignee_entity_id: uuid.UUID | None = None
    parent_document_entity_id: uuid.UUID | None = None
    work_item_entity_id: uuid.UUID | None = None
    # Provider-native reference strings (resolved to UUID FKs in materializer when target exists)
    author_ref: str | None = None
    conversation_ref: str | None = None
    parent_message_ref: str | None = None
    repository_ref: str | None = None
    assignee_ref: str | None = None
    parent_document_ref: str | None = None
    work_item_ref: str | None = None


@dataclass
class CanonMapResult:
    draft: CanonEntityDraft | None
    source: CanonSourceRef
    skip_reason: str | None = None


class CanonMapper(Protocol):
    """Maps one raw ingestion row to zero or one entity draft."""

    resource_type: str

    def map_row(
        self,
        *,
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
        connector: str,
        resource_type: str,
        external_id: str,
        payload_body: dict[str, Any],
        raw_id: int,
        source_identity_key: str,
        source_revision_key: str,
        fetched_at_iso: str,
    ) -> CanonMapResult: ...
