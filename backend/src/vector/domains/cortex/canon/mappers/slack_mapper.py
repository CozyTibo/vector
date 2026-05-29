"""Slack canon mappers."""

from __future__ import annotations

import uuid
from typing import Any

from vector.domains.cortex.canon.mapper_types import CanonEntityDraft, CanonMapResult
from vector.domains.cortex.canon.mappers._common import entity_key_for, label_from_payload, source_ref
from vector.domains.cortex.ingestion.live_idempotency import derive_source_identity_key


def _slack_message_segment(
    payload_body: dict[str, Any],
    resource_type: str,
) -> dict[str, Any] | None:
    if resource_type == "slack.message_reply":
        reply = payload_body.get("reply")
        return reply if isinstance(reply, dict) else None
    for key in ("message", "reply"):
        segment = payload_body.get(key)
        if isinstance(segment, dict):
            return segment
    return None


class _SlackMapper:
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
        label_keys = ("message", "reply", "channel") if self.resource_type == "slack.message_reply" else (
            self.payload_key,
            "channel",
            "message",
        )
        label = label_from_payload(payload_body, *label_keys)
        attrs: dict[str, Any] = {"external_id": external_id}
        draft = CanonEntityDraft(
            entity_type=self.entity_type,
            entity_key=key,
            display_label=label,
            connector=connector,
            connection_id=connection_id,
            attrs_json=attrs,
        )
        if self.entity_type == "actor":
            segment = payload_body.get("member")
            if isinstance(segment, dict):
                attrs["slack_user_id"] = segment.get("id")
        elif self.entity_type == "message":
            msg = _slack_message_segment(payload_body, resource_type)
            cid = payload_body.get("channel_id")
            if not isinstance(cid, str):
                cid = None
            if isinstance(msg, dict):
                uid = msg.get("user")
                if isinstance(uid, str):
                    draft.author_ref = derive_source_identity_key(
                        connector=connector,
                        resource_type="slack.user",
                        external_id=uid,
                    )
                thread_ts = msg.get("thread_ts")
                if resource_type == "slack.message_reply":
                    body_thread_ts = payload_body.get("thread_ts")
                    if isinstance(body_thread_ts, str) and body_thread_ts.strip():
                        thread_ts = body_thread_ts.strip()
                ts = msg.get("ts")
                in_thread = (
                    isinstance(thread_ts, str)
                    and thread_ts.strip()
                    and cid is not None
                    and (
                        resource_type == "slack.message_reply"
                        or (isinstance(ts, str) and thread_ts != ts)
                    )
                )
                if cid is not None:
                    if in_thread:
                        draft.conversation_ref = derive_source_identity_key(
                            connector=connector,
                            resource_type="slack.thread",
                            external_id=f"{cid}:{thread_ts.strip()}",
                        )
                    else:
                        draft.conversation_ref = derive_source_identity_key(
                            connector=connector,
                            resource_type="slack.conversation",
                            external_id=cid,
                        )
                if in_thread:
                    draft.parent_message_ref = derive_source_identity_key(
                        connector=connector,
                        resource_type="slack.message",
                        external_id=f"{cid}:{thread_ts.strip()}",
                    )
        elif self.entity_type == "conversation":
            if resource_type == "slack.thread":
                cid = payload_body.get("channel")
                tts = payload_body.get("thread_ts")
                if isinstance(cid, str) and isinstance(tts, str):
                    attrs["channel_id"] = cid
                    attrs["thread_ts"] = tts
        return CanonMapResult(draft=draft, source=src)


SLACK_MAPPERS: list[_SlackMapper] = [
    _SlackMapper("slack.user", "actor", "member"),
    _SlackMapper("slack.conversation", "conversation", "channel"),
    _SlackMapper("slack.thread", "conversation", "channel"),
    _SlackMapper("slack.message", "message", "message"),
    _SlackMapper("slack.message_changed", "message", "message"),
    _SlackMapper("slack.message_reply", "message", "message"),
]
