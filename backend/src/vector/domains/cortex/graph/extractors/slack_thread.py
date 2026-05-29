"""Slack thread reply edges when canon parent_message_entity_id is not set yet."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.graph.edges import EdgeDraft
from vector.domains.cortex.graph.extractors.phase0_provider_native import _latest_raw
from vector.infrastructure.db.models.canon_entity import CanonEntity


def _resolve_slack_message_by_external_id(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    external_id: str,
) -> uuid.UUID | None:
    return session.scalar(
        select(CanonEntity.id).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.connector == "slack",
            CanonEntity.entity_type == "message",
            CanonEntity.attrs_json["external_id"].astext == external_id,
        ),
    )


def extract_slack_thread_reply_edges(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
) -> list[EdgeDraft]:
    if entity.connector != "slack" or entity.entity_type != "message":
        return []
    if entity.parent_message_entity_id is not None:
        return []

    pair = _latest_raw(session, tenant_id=tenant_id, entity_id=entity.id)
    if pair is None:
        return []
    source, raw = pair
    payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
    cid = payload.get("channel_id")
    if not isinstance(cid, str) or not cid.strip():
        return []

    resource_type = str(raw.resource_type or "")
    thread_ts: str | None = None
    msg_ts: str | None = None

    if resource_type == "slack.message_reply":
        body_thread_ts = payload.get("thread_ts")
        if isinstance(body_thread_ts, str) and body_thread_ts.strip():
            thread_ts = body_thread_ts.strip()
        reply = payload.get("reply")
        if isinstance(reply, dict):
            msg_ts = reply.get("ts") if isinstance(reply.get("ts"), str) else None
    else:
        msg = payload.get("message")
        if isinstance(msg, dict):
            if isinstance(msg.get("thread_ts"), str):
                thread_ts = msg["thread_ts"]
            if isinstance(msg.get("ts"), str):
                msg_ts = msg["ts"]

    if not thread_ts or not thread_ts.strip():
        return []
    if resource_type != "slack.message_reply" and msg_ts == thread_ts:
        return []

    parent_external_id = f"{cid.strip()}:{thread_ts.strip()}"
    parent_id = _resolve_slack_message_by_external_id(
        session,
        tenant_id=tenant_id,
        external_id=parent_external_id,
    )
    if parent_id is None or parent_id == entity.id:
        return []

    return [
        EdgeDraft(
            relationship_kind="replies_to",
            from_entity_id=entity.id,
            to_entity_id=parent_id,
            extractor_rule="text.slack_thread_reply",
            evidence_kind="provider_field",
            evidence_ref="thread_ts",
            evidence_snapshot={
                "channel_id": cid.strip(),
                "thread_ts": thread_ts.strip(),
                "parent_external_id": parent_external_id,
            },
            source_raw_id=int(raw.id),
            source_canon_source_id=source.id,
            observed_at=raw.fetched_at,
            confidence="certain",
        ),
    ]
