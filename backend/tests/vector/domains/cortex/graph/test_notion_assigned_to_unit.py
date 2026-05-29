"""Notion database row assignee graph edges."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

from vector.domains.cortex.graph.extractors.connector_native import extract_connector_native_edges
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def test_notion_database_row_assigned_to_from_people_property() -> None:
    tenant_id = uuid.uuid4()
    row_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    source_id = uuid.uuid4()
    raw_id = 99
    now = datetime.now(UTC)
    notion_user_id = "notion-user-abc"

    entity = CanonEntity(
        id=row_id,
        tenant_id=tenant_id,
        connection_id=uuid.uuid4(),
        connector="notion",
        entity_type="document",
        entity_key="row-1",
        display_label="Task row",
        attrs_json={},
        mapper_version=1,
        materialized_at=now,
    )
    raw = RawIngestionRecord(
        id=raw_id,
        tenant_id=tenant_id,
        connection_id=entity.connection_id,
        connector="notion",
        resource_type="notion.database_row",
        external_id="row-ext",
        api_endpoint="https://api.notion.com",
        query_params={},
        source_identity_key="k",
        source_revision_key="rev",
        idempotency_key="idem",
        payload_hash="h",
        http_status=200,
        payload_body={
            "row": {
                "id": "row-ext",
                "properties": {
                    "Name": {"type": "title", "title": []},
                    "Product owner": {
                        "type": "people",
                        "people": [{"object": "user", "id": notion_user_id}],
                    },
                },
            },
        },
        fetched_at=now,
        run_id=uuid.uuid4(),
    )
    source = CanonEntitySource(
        id=source_id,
        canon_entity_id=row_id,
        raw_id=raw_id,
        connector="notion",
        resource_type="notion.database_row",
        external_id="row-ext",
        source_identity_key="k",
        source_revision_key="rev",
        observed_at=now,
        is_latest=True,
        mapper_version=1,
    )

    session = MagicMock()
    session.execute.return_value.first.return_value = (source, raw)
    session.scalar.return_value = actor_id

    edges = extract_connector_native_edges(session, tenant_id=tenant_id, entity=entity)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.relationship_kind == "assigned_to"
    assert edge.to_entity_id == actor_id
    assert edge.extractor_rule == "notion.property.Product owner.people"
    assert edge.evidence_snapshot["notion_user_id"] == notion_user_id
