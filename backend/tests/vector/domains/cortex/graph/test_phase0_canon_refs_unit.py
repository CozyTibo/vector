"""Unit tests for phase 0 canon ref extractors (no DB)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from vector.domains.cortex.graph.extractors.phase0_canon_refs import extract_canon_ref_edges
from vector.infrastructure.db.models.canon_entity import CanonEntity


def test_extract_authored_by_when_author_ref_set() -> None:
    author_id = uuid.uuid4()
    msg_id = uuid.uuid4()
    entity = CanonEntity(
        id=msg_id,
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="github",
        entity_type="message",
        entity_key="k",
        display_label="comment",
        attrs_json={},
        mapper_version=1,
        materialized_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        author_entity_id=author_id,
    )
    session = MagicMock()
    edges = extract_canon_ref_edges(session, tenant_id=entity.tenant_id, entity=entity)
    assert len(edges) == 1
    assert edges[0].relationship_kind == "authored_by"
    assert edges[0].from_entity_id == msg_id
    assert edges[0].to_entity_id == author_id


def test_extract_replies_to_when_parent_message_set() -> None:
    parent_id = uuid.uuid4()
    reply_id = uuid.uuid4()
    entity = CanonEntity(
        id=reply_id,
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="slack",
        entity_type="message",
        entity_key="k",
        display_label="reply",
        attrs_json={},
        mapper_version=1,
        materialized_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        parent_message_entity_id=parent_id,
    )
    session = MagicMock()
    edges = extract_canon_ref_edges(session, tenant_id=entity.tenant_id, entity=entity)
    assert len(edges) == 1
    assert edges[0].relationship_kind == "replies_to"
    assert edges[0].from_entity_id == reply_id
    assert edges[0].to_entity_id == parent_id
    assert edges[0].extractor_rule == "canon.parent_message_entity_id"
