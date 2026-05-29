"""Phase 1 — deterministic textual reference extraction."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from vector.domains.cortex.graph.edges import EdgeDraft, UnresolvedRefDraft
from vector.domains.cortex.graph.extractors.phase0_provider_native import _latest_raw
from vector.domains.cortex.graph.extractors.text_collect import collect_scannable_text
from vector.domains.cortex.graph.extractors.text_references import (
    extract_reference_edges_from_text,
    repo_full_name_for_entity,
)
from vector.infrastructure.db.models.canon_entity import CanonEntity


@dataclass(frozen=True)
class TextExtractResult:
    edges: list[EdgeDraft]
    unresolved: list[UnresolvedRefDraft]


def extract_text_references(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
) -> TextExtractResult:
    pair = _latest_raw(session, tenant_id=tenant_id, entity_id=entity.id)
    if pair is None:
        return TextExtractResult(edges=[], unresolved=[])
    source, raw = pair
    payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
    observed_at = raw.fetched_at
    edges: list[EdgeDraft] = []
    unresolved: list[UnresolvedRefDraft] = []
    repo_fn = repo_full_name_for_entity(
        session,
        tenant_id=tenant_id,
        entity=entity,
        payload=payload,
    )

    for field_path, text in collect_scannable_text(
        payload,
        entity_type=entity.entity_type,
        connector=entity.connector,
        resource_type=str(raw.resource_type or ""),
    ):
        part_edges, part_unresolved = extract_reference_edges_from_text(
            session,
            tenant_id=tenant_id,
            entity=entity,
            field_path=field_path,
            text=text,
            repo_fn=repo_fn,
            source_raw_id=int(raw.id),
            source_canon_source_id=source.id,
            observed_at=observed_at,
        )
        edges.extend(part_edges)
        unresolved.extend(part_unresolved)

    return TextExtractResult(edges=edges, unresolved=unresolved)
