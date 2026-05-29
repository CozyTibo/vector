"""Unit tests for connector-native graph edges."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from vector.domains.cortex.graph.extractors.connector_native import extract_connector_native_edges
from vector.infrastructure.db.models.canon_entity import CanonEntity


def test_github_issue_comment_comments_on_pr_when_work_item_unset() -> None:
    tenant_id = uuid.uuid4()
    msg_id = uuid.uuid4()
    pr_id = uuid.uuid4()
    now = datetime.now(UTC)

    entity = CanonEntity(
        id=msg_id,
        tenant_id=tenant_id,
        connection_id=uuid.uuid4(),
        connector="github",
        entity_type="message",
        entity_key="k",
        display_label="comment",
        attrs_json={},
        mapper_version=1,
        materialized_at=now,
        work_item_entity_id=None,
    )

    raw = MagicMock()
    raw.id = 1
    raw.external_id = "acme/api#42:issue_comment:9"
    raw.resource_type = "github.issue_comment"
    raw.payload_body = {"comment": {"id": 9}}
    raw.fetched_at = now
    source = MagicMock()
    source.id = 10

    session = MagicMock()
    with (
        patch(
            "vector.domains.cortex.graph.extractors.connector_native._latest_raw",
            return_value=(source, raw),
        ),
        patch(
            "vector.domains.cortex.graph.extractors.connector_native.resolve_entity_id_by_source_identity_key",
            return_value=pr_id,
        ),
    ):
        edges = extract_connector_native_edges(session, tenant_id=tenant_id, entity=entity)

    assert len(edges) == 1
    assert edges[0].relationship_kind == "comments_on"
    assert edges[0].to_entity_id == pr_id


def test_skips_comments_on_when_work_item_already_set() -> None:
    entity = CanonEntity(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="github",
        entity_type="message",
        entity_key="k",
        display_label="c",
        attrs_json={},
        mapper_version=1,
        materialized_at=datetime.now(UTC),
        work_item_entity_id=uuid.uuid4(),
    )
    assert extract_connector_native_edges(MagicMock(), tenant_id=entity.tenant_id, entity=entity) == []
