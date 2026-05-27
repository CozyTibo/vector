"""Notion canon mappers."""

from __future__ import annotations

import uuid
from typing import Any

from vector.domains.cortex.canon.mapper_types import CanonEntityDraft, CanonMapResult
from vector.domains.cortex.canon.mappers._common import entity_key_for, label_from_payload, source_ref
from vector.domains.cortex.ingestion.live_idempotency import derive_source_identity_key


class _NotionMapper:
    resource_type: str
    entity_type: str
    payload_key: str

    def __init__(self, resource_type: str, entity_type: str, payload_key: str) -> None:
        self.resource_type = resource_type
        self.entity_type = entity_type
        self.payload_key = payload_key

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
    ) -> CanonMapResult:
        src = source_ref(
            raw_id=raw_id,
            connector=connector,
            resource_type=resource_type,
            external_id=external_id,
            source_identity_key=source_identity_key,
            source_revision_key=source_revision_key,
            payload_body=payload_body,
            fetched_at_iso=fetched_at_iso,
        )
        key = entity_key_for(
            tenant_id=tenant_id,
            connector=connector,
            resource_type=resource_type,
            external_id=external_id,
        )
        segment = payload_body.get(self.payload_key)
        label = label_from_payload(payload_body, self.payload_key)
        attrs: dict[str, Any] = {"external_id": external_id}
        draft = CanonEntityDraft(
            entity_type=self.entity_type,
            entity_key=key,
            display_label=label,
            connector=connector,
            connection_id=connection_id,
            attrs_json=attrs,
        )
        if isinstance(segment, dict):
            attrs["notion_id"] = segment.get("id")
            parent = segment.get("parent")
            if isinstance(parent, dict):
                pid = parent.get("page_id") or parent.get("database_id") or parent.get("block_id")
                if isinstance(pid, str):
                    parent_rt = "notion.page"
                    if parent.get("type") == "database_id":
                        parent_rt = "notion.database"
                    elif parent.get("type") == "block_id":
                        parent_rt = "notion.block"
                    draft.parent_document_ref = derive_source_identity_key(
                        connector=connector,
                        resource_type=parent_rt,
                        external_id=pid,
                    )
            if self.entity_type == "actor":
                name = segment.get("name")
                if isinstance(name, list):
                    attrs["name"] = " ".join(str(x) for x in name)
        return CanonMapResult(draft=draft, source=src)


NOTION_MAPPERS: list[_NotionMapper] = [
    _NotionMapper("notion.user", "actor", "user"),
    _NotionMapper("notion.page", "document", "page"),
    _NotionMapper("notion.database", "project", "database"),
    _NotionMapper("notion.database_row", "document", "database_row"),
    _NotionMapper("notion.block", "document", "block"),
]
