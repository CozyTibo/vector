"""Unit tests for phase 1 text reference extraction."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from vector.domains.cortex.graph.extractors.phase1_text import extract_text_references
from vector.infrastructure.db.models.canon_entity import CanonEntity


def test_phase1_scans_github_comment_body_for_references() -> None:
    tenant_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    pr_id = uuid.uuid4()
    now = datetime.now(UTC)

    entity = CanonEntity(
        id=entity_id,
        tenant_id=tenant_id,
        connection_id=uuid.uuid4(),
        connector="github",
        entity_type="message",
        entity_key="k",
        display_label="comment",
        attrs_json={},
        mapper_version=1,
        materialized_at=now,
    )

    raw = MagicMock()
    raw.id = 7
    raw.payload_body = {
        "comment": {"body": "See https://github.com/acme/repo/pull/42"},
    }
    raw.fetched_at = now
    source = MagicMock()
    source.id = 1

    from vector.domains.cortex.graph.edges import EdgeDraft

    pr_edge = EdgeDraft(
        relationship_kind="references",
        from_entity_id=entity_id,
        to_entity_id=pr_id,
        extractor_rule="text.github_pr_url",
        evidence_kind="text_pattern",
        evidence_ref="github_pr_url_v1",
        evidence_snapshot={},
        confidence="high",
    )

    session = MagicMock()
    with (
        patch(
            "vector.domains.cortex.graph.extractors.phase1_text._latest_raw",
            return_value=(source, raw),
        ),
        patch(
            "vector.domains.cortex.graph.extractors.phase1_text.repo_full_name_for_entity",
            return_value=None,
        ),
        patch(
            "vector.domains.cortex.graph.extractors.phase1_text.extract_reference_edges_from_text",
            return_value=([pr_edge], []),
        ),
    ):
        result = extract_text_references(session, tenant_id=tenant_id, entity=entity)

    assert len(result.edges) == 1
    assert result.edges[0].to_entity_id == pr_id
