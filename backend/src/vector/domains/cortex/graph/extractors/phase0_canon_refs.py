"""Phase 0 — project canon entity ref columns to graph edges."""

from __future__ import annotations

import uuid
from typing import Any

from vector.domains.cortex.graph.edges import EdgeDraft
from vector.domains.cortex.graph.resolve import resolve_linear_issue_id
from vector.infrastructure.db.models.canon_entity import CanonEntity


def _edge(
    *,
    kind: str,
    from_id: uuid.UUID,
    to_id: uuid.UUID,
    rule: str,
    ref: str,
) -> EdgeDraft:
    return EdgeDraft(
        relationship_kind=kind,
        from_entity_id=from_id,
        to_entity_id=to_id,
        extractor_rule=rule,
        evidence_kind="canon_ref",
        evidence_ref=ref,
        evidence_snapshot={"canon_column": ref},
        confidence="certain",
    )


def extract_canon_ref_edges(
    session: Any,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
) -> list[EdgeDraft]:
    edges: list[EdgeDraft] = []
    eid = entity.id

    if entity.author_entity_id is not None:
        edges.append(
            _edge(
                kind="authored_by",
                from_id=eid,
                to_id=entity.author_entity_id,
                rule="canon.author_entity_id",
                ref="author_entity_id",
            ),
        )
    if entity.assignee_entity_id is not None and entity.entity_type == "work_item":
        edges.append(
            _edge(
                kind="assigned_to",
                from_id=eid,
                to_id=entity.assignee_entity_id,
                rule="canon.assignee_entity_id",
                ref="assignee_entity_id",
            ),
        )
    if entity.conversation_entity_id is not None:
        edges.append(
            _edge(
                kind="attached_to",
                from_id=eid,
                to_id=entity.conversation_entity_id,
                rule="canon.conversation_entity_id",
                ref="conversation_entity_id",
            ),
        )
    if entity.parent_message_entity_id is not None:
        edges.append(
            _edge(
                kind="replies_to",
                from_id=eid,
                to_id=entity.parent_message_entity_id,
                rule="canon.parent_message_entity_id",
                ref="parent_message_entity_id",
            ),
        )
    if entity.repository_entity_id is not None:
        edges.append(
            _edge(
                kind="belongs_to_repo",
                from_id=eid,
                to_id=entity.repository_entity_id,
                rule="canon.repository_entity_id",
                ref="repository_entity_id",
            ),
        )
    if entity.parent_document_entity_id is not None:
        edges.append(
            _edge(
                kind="parent_of",
                from_id=eid,
                to_id=entity.parent_document_entity_id,
                rule="canon.parent_document_entity_id",
                ref="parent_document_entity_id",
            ),
        )
    if entity.work_item_entity_id is not None and entity.entity_type in ("message",):
        edges.append(
            _edge(
                kind="comments_on",
                from_id=eid,
                to_id=entity.work_item_entity_id,
                rule="canon.work_item_entity_id",
                ref="work_item_entity_id",
            ),
        )

    if entity.entity_type == "issue_relation":
        attrs = entity.attrs_json if isinstance(entity.attrs_json, dict) else {}
        left = entity.work_item_entity_id
        related_id = attrs.get("related_issue_id")
        if isinstance(related_id, str) and left is not None:
            right = resolve_linear_issue_id(session, tenant_id=tenant_id, issue_id=related_id)
            if right is not None:
                rel_type = attrs.get("relation_type")
                edges.append(
                    EdgeDraft(
                        relationship_kind="relates_to",
                        from_entity_id=left,
                        to_entity_id=right,
                        extractor_rule="linear.issue_relation",
                        evidence_kind="provider_field",
                        evidence_ref="related_issue_id",
                        evidence_snapshot={
                            "relation_type": rel_type,
                            "related_issue_id": related_id,
                        },
                        confidence="certain",
                    ),
                )

    return edges
