"""Unit tests for Slack thread reply graph extraction."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from vector.domains.cortex.graph.extractors.slack_thread import extract_slack_thread_reply_edges
from vector.infrastructure.db.models.canon_entity import CanonEntity


def test_extract_slack_thread_reply_when_canon_parent_unset() -> None:
    tenant_id = uuid.uuid4()
    reply_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    now = datetime.now(UTC)

    entity = CanonEntity(
        id=reply_id,
        tenant_id=tenant_id,
        connection_id=uuid.uuid4(),
        connector="slack",
        entity_type="message",
        entity_key=f"{tenant_id}:slack:slack.message_reply:C1:100.000:100.001",
        display_label="reply",
        attrs_json={"external_id": "C1:100.000:100.001"},
        mapper_version=1,
        materialized_at=now,
        parent_message_entity_id=None,
    )

    raw = MagicMock()
    raw.id = 10
    raw.resource_type = "slack.message_reply"
    raw.payload_body = {
        "channel_id": "C1",
        "thread_ts": "100.000",
        "reply": {"ts": "100.001", "user": "U1"},
    }
    raw.fetched_at = now
    source = MagicMock()
    source.id = 1

    session = MagicMock()
    session.scalar.return_value = parent_id

    with patch(
        "vector.domains.cortex.graph.extractors.slack_thread._latest_raw",
        return_value=(source, raw),
    ):
        edges = extract_slack_thread_reply_edges(session, tenant_id=tenant_id, entity=entity)

    assert len(edges) == 1
    assert edges[0].relationship_kind == "replies_to"
    assert edges[0].from_entity_id == reply_id
    assert edges[0].to_entity_id == parent_id
    assert edges[0].extractor_rule == "text.slack_thread_reply"


def test_skips_when_canon_parent_already_set() -> None:
    entity = CanonEntity(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="slack",
        entity_type="message",
        entity_key="k",
        display_label="x",
        attrs_json={},
        mapper_version=1,
        materialized_at=datetime.now(UTC),
        parent_message_entity_id=uuid.uuid4(),
    )
    session = MagicMock()
    assert extract_slack_thread_reply_edges(session, tenant_id=entity.tenant_id, entity=entity) == []
