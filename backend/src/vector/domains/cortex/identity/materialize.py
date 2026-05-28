"""Identity resolution pass runtime (v1)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.resolver_version import IDENTITY_RESOLVER_VERSION
from vector.domains.cortex.identity.signals import extract_actor_signal
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_dirty_queue import IdentityDirtyQueue
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.identity_pass_run import IdentityPassRun
from vector.infrastructure.db.models.identity_suggestion import IdentitySuggestion
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

RUN_RUNNING = "RUNNING"
RUN_COMPLETED = "COMPLETED"
RUN_FAILED = "FAILED"


def enqueue_identity_actor(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    canon_entity_id: uuid.UUID,
    reason: str,
) -> None:
    existing = session.scalar(
        select(IdentityDirtyQueue.id)
        .where(
            IdentityDirtyQueue.tenant_id == tenant_id,
            IdentityDirtyQueue.canon_entity_id == canon_entity_id,
            IdentityDirtyQueue.processed_at.is_(None),
        )
        .limit(1),
    )
    if existing is not None:
        return
    session.add(
        IdentityDirtyQueue(
            tenant_id=tenant_id,
            canon_entity_id=canon_entity_id,
            reason=reason[:32],
        ),
    )


def enqueue_all_actor_entities(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    reason: str,
    limit: int = 50000,
) -> int:
    ids = list(
        session.scalars(
            select(CanonEntity.id)
            .where(CanonEntity.tenant_id == tenant_id, CanonEntity.entity_type == "actor")
            .order_by(CanonEntity.materialized_at.desc())
            .limit(max(1, min(limit, 200000))),
        ).all(),
    )
    for eid in ids:
        enqueue_identity_actor(session, tenant_id=tenant_id, canon_entity_id=eid, reason=reason)
    return len(ids)


def _latest_actor_payload(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    canon_entity_id: uuid.UUID,
) -> tuple[CanonEntity, CanonEntitySource, RawIngestionRecord] | None:
    row = session.execute(
        select(CanonEntity, CanonEntitySource, RawIngestionRecord)
        .join(CanonEntitySource, CanonEntitySource.canon_entity_id == CanonEntity.id)
        .join(RawIngestionRecord, RawIngestionRecord.id == CanonEntitySource.raw_id)
        .where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.id == canon_entity_id,
            CanonEntity.entity_type == "actor",
            CanonEntitySource.is_latest.is_(True),
        )
        .limit(1),
    ).first()
    if row is None:
        return None
    return row


def _seed_identity_for_actor(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    canon_entity: CanonEntity,
    source: CanonEntitySource,
    raw: RawIngestionRecord,
) -> dict[str, Any]:
    existing = session.scalar(
        select(IdentityAccount)
        .where(
            IdentityAccount.tenant_id == tenant_id,
            IdentityAccount.canon_entity_id == canon_entity.id,
            IdentityAccount.unlinked_at.is_(None),
        )
        .limit(1),
    )
    if existing is not None:
        return {"outcome": "already_linked", "identity_entity_id": str(existing.identity_entity_id)}

    payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
    signal = extract_actor_signal(
        canon_entity_id=canon_entity.id,
        connector=canon_entity.connector,
        connection_id=canon_entity.connection_id,
        entity_key=canon_entity.entity_key,
        external_id=source.external_id,
        source_revision_key=source.source_revision_key,
        payload_body=payload,
    )
    identity = IdentityEntity(
        tenant_id=tenant_id,
        kind="unknown",
        display_name=canon_entity.display_label[:512],
        primary_email=(next(iter(signal.emails)) if signal.emails else None),
        resolver_version=IDENTITY_RESOLVER_VERSION,
        status="active",
        resolved_at=utc_now(),
    )
    session.add(identity)
    session.flush()
    evidence = {
        "seed": "actor",
        "connector": canon_entity.connector,
        "source_identity_key": source.source_identity_key,
        "emails": sorted(signal.emails),
        "handles": sorted(signal.handles),
        "display_names": sorted(signal.display_names),
        "provider_ids": sorted(signal.provider_ids),
        "bot_reasons": signal.bot_reasons,
    }
    account = IdentityAccount(
        tenant_id=tenant_id,
        identity_entity_id=identity.id,
        canon_entity_id=canon_entity.id,
        connector=canon_entity.connector,
        connection_id=canon_entity.connection_id,
        link_tier="seed",
        link_rule="seed_actor",
        confidence="low",
        evidence_json=evidence,
        linked_at=utc_now(),
    )
    session.add(account)
    return {"outcome": "seeded", "identity_entity_id": str(identity.id)}


def execute_identity_pass_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_trigger: str,
    batch_limit: int,
) -> dict[str, Any]:
    run = IdentityPassRun(
        tenant_id=tenant_id,
        source_trigger=source_trigger,
        status=RUN_RUNNING,
        started_at=utc_now(),
    )
    session.add(run)
    session.flush()
    stats: dict[str, int] = {
        "processed": 0,
        "seeded": 0,
        "already_linked": 0,
        "missing_actor": 0,
        "errors": 0,
    }
    try:
        items = list(
            session.scalars(
                select(IdentityDirtyQueue)
                .where(
                    IdentityDirtyQueue.tenant_id == tenant_id,
                    IdentityDirtyQueue.processed_at.is_(None),
                )
                .order_by(IdentityDirtyQueue.enqueued_at.asc())
                .limit(max(1, min(batch_limit, 5000))),
            ).all(),
        )
        if not items:
            run.status = RUN_COMPLETED
            run.finished_at = utc_now()
            run.stats = stats
            session.flush()
            return {"status": "completed", "run_id": str(run.id), "stats": stats}
        for item in items:
            stats["processed"] += 1
            row = _latest_actor_payload(session, tenant_id=tenant_id, canon_entity_id=item.canon_entity_id)
            if row is None:
                stats["missing_actor"] += 1
                item.processed_at = utc_now()
                item.last_error = "actor_missing"
                continue
            canon_entity, source, raw = row
            try:
                out = _seed_identity_for_actor(
                    session,
                    tenant_id=tenant_id,
                    canon_entity=canon_entity,
                    source=source,
                    raw=raw,
                )
                if out["outcome"] == "seeded":
                    stats["seeded"] += 1
                else:
                    stats["already_linked"] += 1
                item.processed_at = utc_now()
                item.last_error = None
            except Exception as exc:
                stats["errors"] += 1
                item.attempts += 1
                item.last_error = str(exc)[:1000]
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


def rebuild_identities_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_trigger: str = "manual_rebuild",
    batch_limit: int = 1000,
) -> dict[str, Any]:
    session.execute(delete(IdentitySuggestion).where(IdentitySuggestion.tenant_id == tenant_id))
    session.execute(delete(IdentityAccount).where(IdentityAccount.tenant_id == tenant_id))
    session.execute(delete(IdentityEntity).where(IdentityEntity.tenant_id == tenant_id))
    session.execute(delete(IdentityDirtyQueue).where(IdentityDirtyQueue.tenant_id == tenant_id))
    enqueued = enqueue_all_actor_entities(session, tenant_id=tenant_id, reason="rebuild")
    total_stats = {"processed": 0, "seeded": 0, "already_linked": 0, "missing_actor": 0, "errors": 0}
    while True:
        out = execute_identity_pass_for_tenant(
            session,
            tenant_id=tenant_id,
            source_trigger=source_trigger,
            batch_limit=batch_limit,
        )
        stats = out.get("stats") if isinstance(out.get("stats"), dict) else {}
        for key in total_stats:
            total_stats[key] += int(stats.get(key, 0))
        if int(stats.get("processed", 0)) <= 0:
            break
    return {"enqueued": enqueued, "stats": total_stats}

