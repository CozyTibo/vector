"""Regression: expected graph edge kinds per connector are produced from canon refs."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from vector.domains.cortex.graph.extractors.phase0_canon_refs import extract_canon_ref_edges
from vector.infrastructure.db.models.canon_entity import CanonEntity


def _entity(**kwargs: object) -> CanonEntity:
    now = __import__("datetime").datetime.now(__import__("datetime").UTC)
    defaults = dict(
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        entity_key="k",
        display_label="e",
        attrs_json={},
        mapper_version=1,
        materialized_at=now,
    )
    defaults.update(kwargs)
    return CanonEntity(**defaults)  # type: ignore[arg-type]


def test_slack_message_canon_ref_kinds() -> None:
    author = uuid.uuid4()
    channel = uuid.uuid4()
    parent = uuid.uuid4()
    msg_id = uuid.uuid4()
    entity = _entity(
        id=msg_id,
        connector="slack",
        entity_type="message",
        author_entity_id=author,
        conversation_entity_id=channel,
        parent_message_entity_id=parent,
    )
    kinds = {e.relationship_kind for e in extract_canon_ref_edges(MagicMock(), tenant_id=entity.tenant_id, entity=entity)}
    assert kinds == {"authored_by", "attached_to", "replies_to"}


def test_github_issue_canon_ref_kinds() -> None:
    author = uuid.uuid4()
    repo = uuid.uuid4()
    issue_id = uuid.uuid4()
    entity = _entity(
        id=issue_id,
        connector="github",
        entity_type="work_item",
        author_entity_id=author,
        repository_entity_id=repo,
    )
    kinds = {e.relationship_kind for e in extract_canon_ref_edges(MagicMock(), tenant_id=entity.tenant_id, entity=entity)}
    assert kinds == {"authored_by", "belongs_to_repo"}


def test_linear_issue_canon_ref_kinds() -> None:
    author = uuid.uuid4()
    assignee = uuid.uuid4()
    issue_id = uuid.uuid4()
    entity = _entity(
        id=issue_id,
        connector="linear",
        entity_type="work_item",
        author_entity_id=author,
        assignee_entity_id=assignee,
    )
    kinds = {e.relationship_kind for e in extract_canon_ref_edges(MagicMock(), tenant_id=entity.tenant_id, entity=entity)}
    assert kinds == {"authored_by", "assigned_to"}


def test_notion_document_parent_of() -> None:
    parent = uuid.uuid4()
    doc_id = uuid.uuid4()
    entity = _entity(
        id=doc_id,
        connector="notion",
        entity_type="document",
        parent_document_entity_id=parent,
    )
    edges = extract_canon_ref_edges(MagicMock(), tenant_id=entity.tenant_id, entity=entity)
    assert len(edges) == 1
    assert edges[0].relationship_kind == "parent_of"
