"""Provider-specific graph edges from raw payloads (beyond canon ref columns)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.domains.cortex.canon.mappers.notion_people import (
    iter_notion_people_assignments,
    iter_notion_people_involvements,
    iter_notion_relation_targets,
    notion_segment_properties,
)
from vector.domains.cortex.graph.edges import EdgeDraft
from vector.domains.cortex.graph.extractors.phase0_provider_native import _latest_raw
from vector.domains.cortex.graph.resolve import resolve_entity_id_by_source_identity_key, resolve_notion_external_id
from vector.domains.cortex.ingestion.live_idempotency import derive_source_identity_key
from vector.infrastructure.db.models.canon_entity import CanonEntity


def _pr_external_id_from_child(external_id: str, marker: str) -> str | None:
    token = f":{marker}:"
    if token in external_id:
        return external_id.split(token)[0]
    return None


def _notion_people_edge(
    *,
    entity: CanonEntity,
    actor_id: uuid.UUID,
    prop_name: str,
    notion_user_id: str,
    relationship_kind: str,
    source,
    raw,
    observed_at,
) -> EdgeDraft:
    return EdgeDraft(
        relationship_kind=relationship_kind,
        from_entity_id=entity.id,
        to_entity_id=actor_id,
        extractor_rule=f"notion.property.{prop_name}.people",
        evidence_kind="provider_field",
        evidence_ref=f"properties.{prop_name}.people",
        evidence_snapshot={
            "property_name": prop_name,
            "notion_user_id": notion_user_id,
        },
        source_raw_id=int(raw.id),
        source_canon_source_id=source.id,
        observed_at=observed_at,
        confidence="certain",
    )


def extract_connector_native_edges(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
) -> list[EdgeDraft]:
    pair = _latest_raw(session, tenant_id=tenant_id, entity_id=entity.id)
    if pair is None:
        return []
    source, raw = pair
    payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
    resource_type = str(raw.resource_type or "")
    observed_at = raw.fetched_at
    edges: list[EdgeDraft] = []

    if entity.connector == "github" and entity.entity_type == "message":
        pr_ext: str | None = None
        if resource_type == "github.pull_request_review":
            pr_ext = _pr_external_id_from_child(str(raw.external_id or ""), "review")
        elif resource_type == "github.pull_request_review_comment":
            pr_ext = _pr_external_id_from_child(str(raw.external_id or ""), "review_comment")
        elif resource_type == "github.issue_comment":
            pr_ext = _pr_external_id_from_child(str(raw.external_id or ""), "issue_comment")

        if pr_ext and entity.work_item_entity_id is None:
            pr_key = derive_source_identity_key(
                connector="github",
                resource_type="github.pull_request",
                external_id=pr_ext,
            )
            pr_id = resolve_entity_id_by_source_identity_key(
                session,
                tenant_id=tenant_id,
                source_identity_key=pr_key,
            )
            if pr_id is not None:
                edges.append(
                    EdgeDraft(
                        relationship_kind="comments_on",
                        from_entity_id=entity.id,
                        to_entity_id=pr_id,
                        extractor_rule="github.comment.pull_request_ref",
                        evidence_kind="provider_field",
                        evidence_ref="external_id",
                        evidence_snapshot={
                            "resource_type": resource_type,
                            "pull_request_external_id": pr_ext,
                        },
                        source_raw_id=int(raw.id),
                        source_canon_source_id=source.id,
                        observed_at=observed_at,
                        confidence="certain",
                    ),
                )

    if entity.connector == "notion" and entity.entity_type in ("document", "work_item"):
        props = notion_segment_properties(payload)
        for prop_name, notion_user_id in iter_notion_people_assignments(props):
            user_key = derive_source_identity_key(
                connector="notion",
                resource_type="notion.user",
                external_id=notion_user_id,
            )
            actor_id = resolve_entity_id_by_source_identity_key(
                session,
                tenant_id=tenant_id,
                source_identity_key=user_key,
            )
            if actor_id is None:
                continue
            edges.append(
                _notion_people_edge(
                    entity=entity,
                    actor_id=actor_id,
                    prop_name=prop_name,
                    notion_user_id=notion_user_id,
                    relationship_kind="assigned_to",
                    source=source,
                    raw=raw,
                    observed_at=observed_at,
                ),
            )
        for prop_name, notion_user_id in iter_notion_people_involvements(props):
            user_key = derive_source_identity_key(
                connector="notion",
                resource_type="notion.user",
                external_id=notion_user_id,
            )
            actor_id = resolve_entity_id_by_source_identity_key(
                session,
                tenant_id=tenant_id,
                source_identity_key=user_key,
            )
            if actor_id is None:
                continue
            edges.append(
                _notion_people_edge(
                    entity=entity,
                    actor_id=actor_id,
                    prop_name=prop_name,
                    notion_user_id=notion_user_id,
                    relationship_kind="involves",
                    source=source,
                    raw=raw,
                    observed_at=observed_at,
                ),
            )
        for prop_name, target_id in iter_notion_relation_targets(props):
            target_entity_id = resolve_notion_external_id(
                session,
                tenant_id=tenant_id,
                external_id=target_id,
            )
            if target_entity_id is None:
                continue
            edges.append(
                EdgeDraft(
                    relationship_kind="references",
                    from_entity_id=entity.id,
                    to_entity_id=target_entity_id,
                    extractor_rule=f"notion.property.{prop_name}.relation",
                    evidence_kind="provider_field",
                    evidence_ref=f"properties.{prop_name}.relation",
                    evidence_snapshot={
                        "property_name": prop_name,
                        "target_notion_id": target_id,
                    },
                    source_raw_id=int(raw.id),
                    source_canon_source_id=source.id,
                    observed_at=observed_at,
                    confidence="certain",
                ),
            )

    return edges
