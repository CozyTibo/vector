"""Graph projection pass execution."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from vector.domains.cortex.graph.edges import EdgeDraft, UnresolvedRefDraft
from vector.domains.cortex.graph.enqueue import GRAPH_SCOPED_ENTITY_TYPES
from vector.domains.cortex.graph.extractor_version import effective_graph_extractor_version
from vector.domains.cortex.graph.extractors import (
    extract_canon_ref_edges,
    extract_cross_tool_edges,
    extract_provider_native_edges,
    extract_text_references,
)
from vector.domains.cortex.graph.extractors.connector_native import extract_connector_native_edges
from vector.domains.cortex.graph.extractors.slack_thread import extract_slack_thread_reply_edges
from vector.domains.cortex.identity.resolver_version import effective_identity_resolver_version
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.canon_dirty_queue import CanonDirtyQueue
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_materialization_cursor import CanonMaterializationCursor
from vector.infrastructure.db.models.graph_dirty_queue import GraphDirtyQueue
from vector.infrastructure.db.models.graph_pass_run import GraphPassRun
from vector.infrastructure.db.models.graph_relationship import (
    STATUS_ACTIVE,
    STATUS_SUPERSEDED,
    GraphRelationship,
)
from vector.infrastructure.db.models.graph_unresolved_reference import (
    STATUS_UNRESOLVED,
    GraphUnresolvedReference,
)
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

_logger = logging.getLogger(__name__)

RUN_RUNNING = "RUNNING"
RUN_COMPLETED = "COMPLETED"
RUN_FAILED = "FAILED"


def tenant_has_canon_backlog(session: Session, tenant_id: uuid.UUID) -> bool:
    dirty = session.scalar(
        select(CanonDirtyQueue.id)
        .where(
            CanonDirtyQueue.tenant_id == tenant_id,
            CanonDirtyQueue.processed_at.is_(None),
        )
        .limit(1),
    )
    if dirty is not None:
        return True
    cursor = session.scalar(
        select(CanonMaterializationCursor).where(
            CanonMaterializationCursor.tenant_id == tenant_id,
            CanonMaterializationCursor.scope_key == "live",
        ),
    )
    last_raw = int(cursor.last_raw_id) if cursor is not None else 0
    max_raw = session.scalar(
        select(func.max(RawIngestionRecord.id)).where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.replay_job_id.is_(None),
        ),
    )
    return int(max_raw or 0) > last_raw


def _identity_for_actor(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    actor_entity_id: uuid.UUID,
) -> uuid.UUID | None:
    return session.scalar(
        select(IdentityAccount.identity_entity_id).where(
            IdentityAccount.tenant_id == tenant_id,
            IdentityAccount.canon_entity_id == actor_entity_id,
            IdentityAccount.unlinked_at.is_(None),
        ),
    )


def _enrich_edge_identities(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    edge: GraphRelationship,
    resolver_version: int,
) -> bool:
    changed = False
    from_actor = session.get(CanonEntity, edge.from_entity_id)
    to_actor = session.get(CanonEntity, edge.to_entity_id)
    if from_actor is not None and from_actor.entity_type == "actor":
        iid = _identity_for_actor(session, tenant_id=tenant_id, actor_entity_id=from_actor.id)
        if edge.from_identity_id != iid:
            edge.from_identity_id = iid
            changed = True
    if to_actor is not None and to_actor.entity_type == "actor":
        iid = _identity_for_actor(session, tenant_id=tenant_id, actor_entity_id=to_actor.id)
        if edge.to_identity_id != iid:
            edge.to_identity_id = iid
            changed = True
    if changed:
        edge.identity_resolver_version_at_enrich = resolver_version
    return changed


def _observed_at(draft: EdgeDraft, *, fallback: datetime) -> datetime:
    return draft.observed_at if draft.observed_at is not None else fallback


def upsert_edge_draft(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    draft: EdgeDraft,
    extractor_version: int,
    observed_at: datetime,
) -> str:
    existing = session.scalar(
        select(GraphRelationship)
        .where(
            GraphRelationship.tenant_id == tenant_id,
            GraphRelationship.relationship_kind == draft.relationship_kind,
            GraphRelationship.from_entity_id == draft.from_entity_id,
            GraphRelationship.to_entity_id == draft.to_entity_id,
            GraphRelationship.extractor_rule == draft.extractor_rule,
            GraphRelationship.status == STATUS_ACTIVE,
        )
        .limit(1)
        .with_for_update(),
    )
    if existing is not None:
        if (
            existing.extractor_version == extractor_version
            and existing.evidence_ref == draft.evidence_ref
            and existing.source_raw_id == draft.source_raw_id
        ):
            return "unchanged"
        existing.status = STATUS_SUPERSEDED
        session.flush()
    else:
        existing = None

    row = GraphRelationship(
        tenant_id=tenant_id,
        relationship_kind=draft.relationship_kind,
        from_entity_id=draft.from_entity_id,
        to_entity_id=draft.to_entity_id,
        confidence=draft.confidence,
        extractor_version=extractor_version,
        extractor_rule=draft.extractor_rule,
        evidence_kind=draft.evidence_kind,
        evidence_ref=draft.evidence_ref,
        evidence_snapshot=draft.evidence_snapshot,
        source_raw_id=draft.source_raw_id,
        source_canon_source_id=draft.source_canon_source_id,
        observed_at=_observed_at(draft, fallback=observed_at),
        status=STATUS_ACTIVE,
        created_at=utc_now(),
    )
    session.add(row)
    session.flush()
    if existing is not None:
        existing.superseded_by_id = row.id
    return "upserted"


def _record_unresolved(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_entity_id: uuid.UUID,
    source_raw_id: int | None,
    draft: UnresolvedRefDraft,
) -> None:
    existing = session.scalar(
        select(GraphUnresolvedReference.id)
        .where(
            GraphUnresolvedReference.tenant_id == tenant_id,
            GraphUnresolvedReference.source_entity_id == source_entity_id,
            GraphUnresolvedReference.reference_text == draft.reference_text[:512],
            GraphUnresolvedReference.status == STATUS_UNRESOLVED,
        )
        .limit(1),
    )
    if existing is not None:
        return
    session.add(
        GraphUnresolvedReference(
            tenant_id=tenant_id,
            source_entity_id=source_entity_id,
            source_raw_id=source_raw_id,
            reference_kind=draft.reference_kind,
            reference_text=draft.reference_text[:512],
            extractor_rule=draft.extractor_rule,
            evidence_snapshot=draft.evidence_snapshot,
            status=STATUS_UNRESOLVED,
            created_at=utc_now(),
        ),
    )


def _extract_edges_for_entity(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
) -> tuple[list[EdgeDraft], list[UnresolvedRefDraft]]:
    drafts = extract_canon_ref_edges(session, tenant_id=tenant_id, entity=entity)
    drafts.extend(extract_slack_thread_reply_edges(session, tenant_id=tenant_id, entity=entity))
    drafts.extend(extract_connector_native_edges(session, tenant_id=tenant_id, entity=entity))
    drafts.extend(extract_provider_native_edges(session, tenant_id=tenant_id, entity=entity))
    text_out = extract_text_references(session, tenant_id=tenant_id, entity=entity)
    drafts.extend(text_out.edges)
    unresolved = list(text_out.unresolved)
    cross_edges, cross_unresolved = extract_cross_tool_edges(
        session,
        tenant_id=tenant_id,
        entity=entity,
    )
    drafts.extend(cross_edges)
    unresolved.extend(cross_unresolved)
    return drafts, unresolved


def _process_entity_extract(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
    extractor_version: int,
    identity_resolver_version: int | None,
    stats: dict[str, int],
) -> None:
    now = utc_now()
    edge_drafts, unresolved_drafts = _extract_edges_for_entity(
        session,
        tenant_id=tenant_id,
        entity=entity,
    )
    for draft in edge_drafts:
        outcome = upsert_edge_draft(
            session,
            tenant_id=tenant_id,
            draft=draft,
            extractor_version=extractor_version,
            observed_at=now,
        )
        if outcome == "upserted":
            stats["edges_upserted"] += 1
        elif outcome == "unchanged":
            stats["edges_unchanged"] += 1
    pair = None
    from vector.domains.cortex.graph.extractors.phase0_provider_native import _latest_raw

    pair = _latest_raw(session, tenant_id=tenant_id, entity_id=entity.id)
    raw_id = int(pair[1].id) if pair is not None else None
    for udraft in unresolved_drafts:
        _record_unresolved(
            session,
            tenant_id=tenant_id,
            source_entity_id=entity.id,
            source_raw_id=raw_id,
            draft=udraft,
        )
        stats["unresolved_refs"] += 1
    resolver_version = effective_identity_resolver_version(identity_resolver_version)
    active_edges = session.scalars(
        select(GraphRelationship).where(
            GraphRelationship.tenant_id == tenant_id,
            GraphRelationship.status == STATUS_ACTIVE,
            (
                (GraphRelationship.from_entity_id == entity.id)
                | (GraphRelationship.to_entity_id == entity.id)
            ),
        ),
    ).all()
    for edge in active_edges:
        if _enrich_edge_identities(
            session,
            tenant_id=tenant_id,
            edge=edge,
            resolver_version=resolver_version,
        ):
            stats["edges_enriched"] += 1


def _process_entity_enrich_only(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
    resolver_version: int,
    stats: dict[str, int],
) -> None:
    edges = session.scalars(
        select(GraphRelationship).where(
            GraphRelationship.tenant_id == tenant_id,
            GraphRelationship.status == STATUS_ACTIVE,
            (
                (GraphRelationship.from_entity_id == entity.id)
                | (GraphRelationship.to_entity_id == entity.id)
            ),
        ),
    ).all()
    for edge in edges:
        if _enrich_edge_identities(
            session,
            tenant_id=tenant_id,
            edge=edge,
            resolver_version=resolver_version,
        ):
            stats["edges_enriched"] += 1


def _fetch_dirty_batch(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    batch_limit: int,
    max_attempts: int,
) -> list[GraphDirtyQueue]:
    cap = max(1, min(batch_limit, 5000))
    attempt_cap = max(1, max_attempts)
    return list(
        session.scalars(
            select(GraphDirtyQueue)
            .where(
                GraphDirtyQueue.tenant_id == tenant_id,
                GraphDirtyQueue.processed_at.is_(None),
                GraphDirtyQueue.attempts < attempt_cap,
            )
            .order_by(GraphDirtyQueue.enqueued_at.asc())
            .limit(cap),
        ).all(),
    )


def execute_graph_projection_pass_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_trigger: str,
    batch_limit: int,
    max_attempts: int = 5,
    extractor_version: int | None = None,
    identity_resolver_version: int | None = None,
    drain: bool | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    if drain is None:
        drain = source_trigger == "manual_admin"
    resolved_extractor = effective_graph_extractor_version(extractor_version)
    resolved_identity = effective_identity_resolver_version(identity_resolver_version)
    enrich_only = mode == "enrich_identity_only"

    if not enrich_only and tenant_has_canon_backlog(session, tenant_id):
        return {
            "status": "skipped",
            "reason": "canon_backlog",
            "stats": {},
        }

    run = GraphPassRun(
        tenant_id=tenant_id,
        source_trigger=source_trigger,
        status=RUN_RUNNING,
        started_at=utc_now(),
    )
    session.add(run)
    session.flush()

    stats: dict[str, int] = {
        "processed": 0,
        "edges_upserted": 0,
        "edges_unchanged": 0,
        "edges_enriched": 0,
        "unresolved_refs": 0,
        "errors": 0,
    }
    max_iterations = 100 if drain else 1
    try:
        for _ in range(max_iterations):
            items = _fetch_dirty_batch(
                session,
                tenant_id=tenant_id,
                batch_limit=batch_limit,
                max_attempts=max_attempts,
            )
            if not items:
                break
            for item in items:
                stats["processed"] += 1
                entity = session.get(CanonEntity, item.canon_entity_id)
                if entity is None or entity.tenant_id != tenant_id:
                    item.processed_at = utc_now()
                    item.last_error = "entity_missing"
                    continue
                try:
                    if enrich_only or item.reason == "identity_linked":
                        _process_entity_enrich_only(
                            session,
                            tenant_id=tenant_id,
                            entity=entity,
                            resolver_version=resolved_identity,
                            stats=stats,
                        )
                    elif entity.entity_type in GRAPH_SCOPED_ENTITY_TYPES:
                        _process_entity_extract(
                            session,
                            tenant_id=tenant_id,
                            entity=entity,
                            extractor_version=resolved_extractor,
                            identity_resolver_version=resolved_identity,
                            stats=stats,
                        )
                    item.processed_at = utc_now()
                    item.last_error = None
                except Exception as exc:
                    stats["errors"] += 1
                    item.attempts += 1
                    item.last_error = str(exc)[:1000]
                    _logger.exception(
                        "graph projection entity failed tenant=%s entity=%s",
                        tenant_id,
                        entity.id,
                    )
            if not drain:
                break
        run.status = RUN_COMPLETED
        run.finished_at = utc_now()
        run.stats = stats
        session.flush()
        return {"status": "completed", "run_id": str(run.id), "stats": stats}
    except Exception as exc:
        run.status = RUN_FAILED
        run.finished_at = utc_now()
        run.error_summary = str(exc)[:2000]
        run.stats = stats
        session.flush()
        raise


def prepare_graph_rebuild_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Supersede active edges, clear dirty queue, and enqueue all scoped canon entities."""
    session.execute(
        update(GraphRelationship)
        .where(
            GraphRelationship.tenant_id == tenant_id,
            GraphRelationship.status == STATUS_ACTIVE,
        )
        .values(status=STATUS_SUPERSEDED),
    )
    session.execute(delete(GraphDirtyQueue).where(GraphDirtyQueue.tenant_id == tenant_id))
    ids = list(
        session.scalars(
            select(CanonEntity.id).where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.entity_type.in_(tuple(sorted(GRAPH_SCOPED_ENTITY_TYPES))),
            ),
        ).all(),
    )
    from vector.domains.cortex.graph.enqueue import enqueue_graph_entity

    for eid in ids:
        enqueue_graph_entity(
            session,
            tenant_id=tenant_id,
            canon_entity_id=eid,
            reason="rebuild",
        )
    return {"enqueued_entity_count": len(ids)}


def rebuild_graph_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_trigger: str = "manual_rebuild",
    batch_limit: int = 1000,
    extractor_version: int | None = None,
) -> dict[str, Any]:
    """Synchronous rebuild (scripts/tests). Admin uses prepare + async cortex pass."""
    prep = prepare_graph_rebuild_for_tenant(session, tenant_id=tenant_id)
    out = execute_graph_projection_pass_for_tenant(
        session,
        tenant_id=tenant_id,
        source_trigger=source_trigger,
        batch_limit=batch_limit,
        extractor_version=extractor_version,
        drain=True,
    )
    out["enqueued_entity_count"] = prep["enqueued_entity_count"]
    return out
