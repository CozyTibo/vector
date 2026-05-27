"""Linear canon mappers."""

from __future__ import annotations

import uuid
from typing import Any

from vector.domains.cortex.canon.mapper_types import CanonEntityDraft, CanonMapResult
from vector.domains.cortex.canon.mappers._common import entity_key_for, label_from_payload, source_ref
from vector.domains.cortex.ingestion.live_idempotency import derive_source_identity_key


def _linear_user_ref(connector: str, user: dict[str, Any]) -> str | None:
    uid = user.get("id")
    if not isinstance(uid, str) or not uid:
        return None
    return derive_source_identity_key(connector=connector, resource_type="linear.user", external_id=uid)


class _LinearMapper:
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
            if self.entity_type == "work_item":
                attrs["identifier"] = segment.get("identifier")
                attrs["state"] = segment.get("state", {}).get("name") if isinstance(segment.get("state"), dict) else segment.get("state")
                assignee = segment.get("assignee")
                if isinstance(assignee, dict):
                    draft.assignee_ref = _linear_user_ref(connector, assignee)
            elif self.entity_type == "message":
                user = segment.get("user")
                if isinstance(user, dict):
                    draft.author_ref = _linear_user_ref(connector, user)
                issue_id = payload_body.get("issue_id")
                if isinstance(issue_id, str):
                    draft.work_item_ref = derive_source_identity_key(
                        connector=connector,
                        resource_type="linear.issue",
                        external_id=issue_id,
                    )
            elif self.entity_type == "actor":
                attrs["name"] = segment.get("name")
                attrs["email"] = segment.get("email")
            elif self.entity_type == "project":
                attrs["name"] = segment.get("name")
        return CanonMapResult(draft=draft, source=src)


LINEAR_MAPPERS: list[_LinearMapper] = [
    _LinearMapper("linear.user", "actor", "user"),
    _LinearMapper("linear.issue", "work_item", "issue"),
    _LinearMapper("linear.comment", "message", "comment"),
    _LinearMapper("linear.comment_thread", "conversation", "comment_thread"),
    _LinearMapper("linear.project", "project", "project"),
]
