"""GitHub PR head_commit graph edges."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

from vector.domains.cortex.graph.extractors.phase0_provider_native import extract_provider_native_edges
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def test_pull_request_head_commit_edge() -> None:
    tenant_id = uuid.uuid4()
    pr_id = uuid.uuid4()
    commit_id = uuid.uuid4()
    source_id = uuid.uuid4()
    raw_id = 42
    now = datetime.now(UTC)

    entity = CanonEntity(
        id=pr_id,
        tenant_id=tenant_id,
        connection_id=uuid.uuid4(),
        connector="github",
        entity_type="pull_request",
        entity_key="pr-1",
        display_label="PR 1",
        attrs_json={},
        mapper_version=1,
        materialized_at=now,
    )
    raw = RawIngestionRecord(
        id=raw_id,
        tenant_id=tenant_id,
        connection_id=entity.connection_id,
        connector="github",
        resource_type="github.pull_request",
        external_id="pr-ext",
        api_endpoint="https://api.github.com",
        query_params={},
        source_identity_key="k",
        source_revision_key="rev",
        idempotency_key="idem",
        payload_hash="h",
        http_status=200,
        payload_body={
            "pull_request": {
                "head": {"sha": "abc123def456"},
                "merge_commit_sha": "merge999",
            },
        },
        fetched_at=now,
        run_id=uuid.uuid4(),
    )
    source = CanonEntitySource(
        id=source_id,
        canon_entity_id=pr_id,
        raw_id=raw_id,
        connector="github",
        resource_type="github.pull_request",
        external_id="pr-ext",
        source_identity_key="k",
        source_revision_key="rev",
        observed_at=now,
        is_latest=True,
        mapper_version=1,
    )

    session = MagicMock()
    session.execute.return_value.first.return_value = (source, raw)

    def _scalar(stmt: object) -> uuid.UUID | None:
        _ = stmt
        return commit_id

    session.scalar.side_effect = _scalar

    edges = extract_provider_native_edges(session, tenant_id=tenant_id, entity=entity)
    kinds = {e.relationship_kind: e for e in edges}
    assert "head_commit" in kinds
    assert kinds["head_commit"].extractor_rule == "github.pull_request.head.sha"
    assert kinds["head_commit"].to_entity_id == commit_id
    assert "merged_as_commit" in kinds
