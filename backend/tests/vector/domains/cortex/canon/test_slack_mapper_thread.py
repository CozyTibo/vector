"""Slack mapper thread parent refs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.domains.cortex.canon.mappers.slack_mapper import SLACK_MAPPERS


def _mapper_for(resource_type: str):
    for m in SLACK_MAPPERS:
        if m.resource_type == resource_type:
            return m
    raise AssertionError(f"no mapper for {resource_type}")


def test_message_reply_attaches_to_thread_conversation() -> None:
    mapper = _mapper_for("slack.message_reply")
    tenant_id = uuid.uuid4()
    result = mapper.map_row(
        tenant_id=tenant_id,
        connection_id=uuid.uuid4(),
        connector="slack",
        resource_type="slack.message_reply",
        external_id="C1:100.000:100.001",
        payload_body={
            "channel_id": "C1",
            "thread_ts": "100.000",
            "reply": {"ts": "100.001", "user": "U1", "text": "follow-up"},
        },
        raw_id=1,
        source_identity_key="slack:slack.message_reply:C1:100.000:100.001",
        source_revision_key="h1",
        fetched_at_iso=datetime.now(UTC).isoformat(),
    )
    assert result.draft is not None
    assert result.draft.conversation_ref is not None
    assert "slack.thread:C1:100.000" in (result.draft.conversation_ref or "")


def test_message_reply_sets_parent_message_ref_to_thread_root() -> None:
    mapper = _mapper_for("slack.message_reply")
    tenant_id = uuid.uuid4()
    conn_id = uuid.uuid4()
    result = mapper.map_row(
        tenant_id=tenant_id,
        connection_id=conn_id,
        connector="slack",
        resource_type="slack.message_reply",
        external_id="C1:100.000:100.001",
        payload_body={
            "channel_id": "C1",
            "thread_ts": "100.000",
            "reply": {"ts": "100.001", "user": "U1", "text": "follow-up"},
        },
        raw_id=1,
        source_identity_key="slack:slack.message_reply:C1:100.000:100.001",
        source_revision_key="h1",
        fetched_at_iso=datetime.now(UTC).isoformat(),
    )
    assert result.draft is not None
    assert result.draft.parent_message_ref is not None
    assert result.draft.parent_message_ref.endswith("slack.message:C1:100.000")
    assert result.draft.author_ref is not None


def test_channel_message_in_thread_sets_parent_ref() -> None:
    mapper = _mapper_for("slack.message")
    tenant_id = uuid.uuid4()
    result = mapper.map_row(
        tenant_id=tenant_id,
        connection_id=uuid.uuid4(),
        connector="slack",
        resource_type="slack.message",
        external_id="C1:100.001",
        payload_body={
            "channel_id": "C1",
            "message": {"ts": "100.001", "thread_ts": "100.000", "user": "U1", "text": "reply"},
        },
        raw_id=2,
        source_identity_key="slack:slack.message:C1:100.001",
        source_revision_key="h2",
        fetched_at_iso=datetime.now(UTC).isoformat(),
    )
    assert result.draft is not None
    assert result.draft.parent_message_ref is not None
    assert "C1:100.000" in (result.draft.parent_message_ref or "")


def test_thread_root_has_no_parent_ref() -> None:
    mapper = _mapper_for("slack.message")
    result = mapper.map_row(
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="slack",
        resource_type="slack.message",
        external_id="C1:100.000",
        payload_body={
            "channel_id": "C1",
            "message": {"ts": "100.000", "thread_ts": "100.000", "user": "U1", "text": "root"},
        },
        raw_id=3,
        source_identity_key="slack:slack.message:C1:100.000",
        source_revision_key="h3",
        fetched_at_iso=datetime.now(UTC).isoformat(),
    )
    assert result.draft is not None
    assert result.draft.parent_message_ref is None
