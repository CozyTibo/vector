"""Canon materialization — raw rows to substrate entities."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.mapper_registry import mapper_for_resource_type
from vector.domains.cortex.canon.mapper_types import CanonEntityDraft
from vector.domains.cortex.canon.mapper_version import CANON_MAPPER_VERSION
from vector.domains.cortex.canon.resource_type_registry import should_materialize_resource_type
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.canon_dirty_queue import CanonDirtyQueue
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.canon_materialization_cursor import CanonMaterializationCursor
from vector.infrastructure.db.models.canon_pass_run import CanonPassRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

_logger = logging.getLogger("app")

RUN_RUNNING = "RUNNING"
RUN_COMPLETED = "COMPLETED"
RUN_FAILED = "FAILED"


def enqueue_dirty_identity(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    source_identity_key: str,
    reason: str = "new_raw",
) -> None:
    existing = session.scalar(
        select(CanonDirtyQueue.id)
        .where(
            CanonDirtyQueue.tenant_id == tenant_id,
            CanonDirtyQueue.source_identity_key == source_identity_key,
            CanonDirtyQueue.processed_at.is_(None),
        )
        .limit(1),
    )
    if existing is not None:
        return
    session.add(
        CanonDirtyQueue(
            tenant_id=tenant_id,
            connection_id=connection_id,
            source_identity_key=source_identity_key,
            reason=reason,
        ),
    )


def _resolve_entity_id(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    ref_identity_key: str,
) -> uuid.UUID | None:
    """Resolve provider identity key to canon entity id (same tenant)."""
    entity_key = f"{tenant_id}:{ref_identity_key}"[:512]
    return session.scalar(
        select(CanonEntity.id).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.entity_key == entity_key,
        ),
    )


def _apply_refs(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    draft: CanonEntityDraft,
    entity: CanonEntity,
) -> None:
    pairs = (
        ("author_ref", "author_entity_id"),
        ("conversation_ref", "conversation_entity_id"),
        ("parent_message_ref", "parent_message_entity_id"),
        ("repository_ref", "repository_entity_id"),
        ("assignee_ref", "assignee_entity_id"),
        ("parent_document_ref", "parent_document_entity_id"),
        ("work_item_ref", "work_item_entity_id"),
    )
    for ref_attr, fk_attr in pairs:
        ref = getattr(draft, ref_attr)
        if not ref:
            continue
        target_id = _resolve_entity_id(session, tenant_id=tenant_id, ref_identity_key=ref)
        if target_id is not None:
            setattr(entity, fk_attr, target_id)


def materialize_raw_row(session: Session, row: RawIngestionRecord) -> dict[str, Any]:
    """Map and persist one raw row; returns outcome dict."""
    if row.replay_job_id is not None:
        return {"outcome": "skipped_replay"}
    if not should_materialize_resource_type(row.resource_type):
        return {"outcome": "skipped_registry"}
    mapper = mapper_for_resource_type(row.resource_type)
    if mapper is None:
        return {"outcome": "skipped_no_mapper"}
    result = mapper.map_row(
        tenant_id=row.tenant_id,
        connection_id=row.connection_id,
        connector=row.connector,
        resource_type=row.resource_type,
        external_id=row.external_id,
        payload_body=dict(row.payload_body),
        raw_id=int(row.id),
        source_identity_key=row.source_identity_key,
        source_revision_key=row.source_revision_key,
        fetched_at_iso=row.fetched_at.isoformat(),
    )
    if result.draft is None:
        return {"outcome": "skipped_mapper", "reason": result.skip_reason}
    draft = result.draft
    now = utc_now()
    entity = session.scalar(
        select(CanonEntity).where(
            CanonEntity.tenant_id == row.tenant_id,
            CanonEntity.entity_type == draft.entity_type,
            CanonEntity.entity_key == draft.entity_key,
        ),
    )
    if entity is None:
        entity = CanonEntity(
            id=uuid.uuid4(),
            tenant_id=row.tenant_id,
            connection_id=draft.connection_id,
            connector=draft.connector,
            entity_type=draft.entity_type,
            entity_key=draft.entity_key,
            display_label=draft.display_label,
            attrs_json=dict(draft.attrs_json),
            mapper_version=CANON_MAPPER_VERSION,
            materialized_at=now,
        )
        session.add(entity)
        session.flush()
    else:
        entity.display_label = draft.display_label
        entity.attrs_json = dict(draft.attrs_json)
        entity.mapper_version = CANON_MAPPER_VERSION
        entity.materialized_at = now
        entity.connection_id = draft.connection_id
        entity.connector = draft.connector

    _apply_refs(session, tenant_id=row.tenant_id, draft=draft, entity=entity)
    if draft.entity_type == "actor":
        try:
            from vector.domains.cortex.identity.materialize import enqueue_identity_actor

            enqueue_identity_actor(
                session,
                tenant_id=row.tenant_id,
                canon_entity_id=entity.id,
                reason="actor_materialized",
            )
        except Exception:
            # Identity queueing is best-effort and must not break canon materialization.
            _logger.exception("identity enqueue failed during canon materialization")

    observed = datetime.fromisoformat(result.source.observed_at_iso.replace("Z", "+00:00"))
    session.execute(
        update(CanonEntitySource)
        .where(
            CanonEntitySource.canon_entity_id == entity.id,
            CanonEntitySource.is_latest.is_(True),
        )
        .values(is_latest=False),
    )
    ins = (
        pg_insert(CanonEntitySource.__table__)
        .values(
            canon_entity_id=entity.id,
            raw_id=row.id,
            connector=result.source.connector,
            resource_type=result.source.resource_type,
            external_id=result.source.external_id,
            source_identity_key=result.source.source_identity_key,
            source_revision_key=result.source.source_revision_key,
            observed_at=observed,
            is_latest=True,
            mapper_version=CANON_MAPPER_VERSION,
        )
        .on_conflict_do_nothing(
            constraint="uq_canon_entity_sources_entity_revision_mapper",
        )
    )
    session.execute(ins)
    return {"outcome": "materialized", "entity_id": str(entity.id)}


def _get_or_create_cursor(session: Session, tenant_id: uuid.UUID, *, scope_key: str = "live") -> CanonMaterializationCursor:
    cur = session.get(CanonMaterializationCursor, {"tenant_id": tenant_id, "scope_key": scope_key})
    if cur is None:
        cur = CanonMaterializationCursor(
            tenant_id=tenant_id,
            scope_key=scope_key,
            last_raw_id=0,
            mapper_version=CANON_MAPPER_VERSION,
        )
        session.add(cur)
        session.flush()
    return cur


def execute_canon_pass_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_trigger: str,
    batch_limit: int,
    scope_key: str = "live",
) -> dict[str, Any]:
    """Run one canon pass: scan raw rows after cursor, materialize, advance cursor."""
    run = CanonPassRun(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        source_trigger=source_trigger,
        status=RUN_RUNNING,
        started_at=utc_now(),
    )
    session.add(run)
    session.flush()
    stats: dict[str, Any] = {
        "scanned": 0,
        "materialized": 0,
        "skipped": 0,
        "errors": 0,
    }
    try:
        cursor = _get_or_create_cursor(session, tenant_id, scope_key=scope_key)
        last_id = int(cursor.last_raw_id)
        rows = list(
            session.scalars(
                select(RawIngestionRecord)
                .where(
                    RawIngestionRecord.tenant_id == tenant_id,
                    RawIngestionRecord.id > last_id,
                    RawIngestionRecord.replay_job_id.is_(None),
                )
                .order_by(RawIngestionRecord.id.asc())
                .limit(batch_limit),
            ).all(),
        )
        max_id = last_id
        for row in rows:
            stats["scanned"] += 1
            max_id = max(max_id, int(row.id))
            try:
                out = materialize_raw_row(session, row)
                if out.get("outcome") == "materialized":
                    stats["materialized"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as exc:
                stats["errors"] += 1
                _logger.warning(
                    "canon materialize row failed",
                    extra={"raw_id": row.id, "error": str(exc)},
                )
        cursor.last_raw_id = max_id
        cursor.mapper_version = CANON_MAPPER_VERSION
        cursor.updated_at = utc_now()
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


def process_dirty_queue_batch(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    batch_limit: int,
) -> dict[str, Any]:
    """Materialize identities enqueued on dirty queue."""
    items = list(
        session.scalars(
            select(CanonDirtyQueue)
            .where(
                CanonDirtyQueue.tenant_id == tenant_id,
                CanonDirtyQueue.processed_at.is_(None),
            )
            .order_by(CanonDirtyQueue.enqueued_at.asc())
            .limit(batch_limit),
        ).all(),
    )
    stats = {"processed": 0, "materialized": 0, "errors": 0}
    for item in items:
        stats["processed"] += 1
        row = session.scalar(
            select(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.source_identity_key == item.source_identity_key,
                RawIngestionRecord.replay_job_id.is_(None),
            )
            .order_by(RawIngestionRecord.id.desc())
            .limit(1),
        )
        if row is None:
            item.processed_at = utc_now()
            item.last_error = "no_raw_row"
            continue
        try:
            out = materialize_raw_row(session, row)
            if out.get("outcome") == "materialized":
                stats["materialized"] += 1
            item.processed_at = utc_now()
        except Exception as exc:
            stats["errors"] += 1
            item.attempts += 1
            item.last_error = str(exc)[:1000]
    session.flush()
    return stats
