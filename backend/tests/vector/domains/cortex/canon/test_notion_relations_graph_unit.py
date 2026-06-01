"""Notion relation and people graph edge unit tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

from vector.domains.cortex.graph.extractors.connector_native import extract_connector_native_edges
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def test_notion_relation_and_involves_edges() -> None:
    tenant_id = uuid.uuid4()
    row_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()
    source_id = uuid.uuid4()
    raw_id = 101
    now = datetime.now(UTC)

    entity = CanonEntity(
        id=row_id,
        tenant_id=tenant_id,
        connection_id=uuid.uuid4(),
        connector="notion",
        entity_type="work_item",
        entity_key="row-1",
        display_label="Task",
        attrs_json={},
        mapper_version=2,
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
                "properties": {
                    "Related project": {
                        "type": "relation",
                        "relation": [{"id": "target-page"}],
                    },
                    "Attendees": {
                        "type": "people",
                        "people": [{"id": "user-1"}],
                    },
                    "Product owner": {
                        "type": "people",
                        "people": [{"id": "user-2"}],
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
        mapper_version=2,
    )

    session = MagicMock()
    session.execute.return_value.first.return_value = (source, raw)

    target_entity = CanonEntity(
        id=target_id,
        tenant_id=tenant_id,
        connection_id=entity.connection_id,
        connector="notion",
        entity_type="document",
        entity_key=f"{tenant_id}:notion:notion.page:target-page",
        display_label="Target",
        attrs_json={"notion_id": "target-page", "external_id": "target-page"},
        mapper_version=2,
        materialized_at=now,
    )
    session.scalar.side_effect = [actor_id, actor_id]
    session.scalars.return_value.all.return_value = [target_entity]

    edges = extract_connector_native_edges(session, tenant_id=tenant_id, entity=entity)
    kinds = {edge.relationship_kind for edge in edges}
    assert "assigned_to" in kinds
    assert "involves" in kinds
    assert "references" in kinds
