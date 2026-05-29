"""Graph edges from Linear issue_relation canon rows."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from vector.domains.cortex.graph.extractors.phase0_canon_refs import extract_canon_ref_edges
from vector.infrastructure.db.models.canon_entity import CanonEntity


def _entity(**kwargs: object) -> CanonEntity:
    now = __import__("datetime").datetime.now(__import__("datetime").UTC)
    defaults = dict(
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        entity_key="k",
        display_label="rel",
        attrs_json={},
        mapper_version=1,
        materialized_at=now,
    )
    defaults.update(kwargs)
    return CanonEntity(**defaults)  # type: ignore[arg-type]


@patch("vector.domains.cortex.graph.extractors.phase0_canon_refs.resolve_linear_issue_id")
def test_issue_relation_blocks_edge(mock_resolve: MagicMock) -> None:
    left = uuid.uuid4()
    right = uuid.uuid4()
    mock_resolve.return_value = right
    entity = _entity(
        id=uuid.uuid4(),
        connector="linear",
        entity_type="issue_relation",
        work_item_entity_id=left,
        attrs_json={"related_issue_id": "iss-2", "relation_type": "blocks"},
    )
    edges = extract_canon_ref_edges(MagicMock(), tenant_id=entity.tenant_id, entity=entity)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.relationship_kind == "blocks"
    assert edge.from_entity_id == left
    assert edge.to_entity_id == right
    assert edge.extractor_rule == "linear.issue_relation.blocks"


@patch("vector.domains.cortex.graph.extractors.phase0_canon_refs.resolve_linear_issue_id")
def test_issue_relation_duplicate_edge(mock_resolve: MagicMock) -> None:
    left = uuid.uuid4()
    right = uuid.uuid4()
    mock_resolve.return_value = right
    entity = _entity(
        id=uuid.uuid4(),
        connector="linear",
        entity_type="issue_relation",
        work_item_entity_id=left,
        attrs_json={"related_issue_id": "iss-9", "relation_type": "duplicate"},
    )
    edges = extract_canon_ref_edges(MagicMock(), tenant_id=entity.tenant_id, entity=entity)
    assert len(edges) == 1
    assert edges[0].relationship_kind == "duplicates"
    assert edges[0].extractor_rule == "linear.issue_relation.duplicates"
