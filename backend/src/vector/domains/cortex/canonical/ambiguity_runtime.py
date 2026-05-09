"""Phase 03 Step 7 — ambiguity persistence + lifecycle (append-only event log).

Normative: `DOCS/cortex/03-canonical/phase-03-ambiguity-confidence-doctrine.md`.
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any, Final

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from vector.infrastructure.db.models.cortex_canonical_ambiguity_lifecycle_event import (
    CortexCanonicalAmbiguityLifecycleEvent,
)
from vector.infrastructure.db.models.cortex_canonical_ambiguity_record import CortexCanonicalAmbiguityRecord
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

AMBIGUITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1
AMBIGUITY_ENGINE_BUILD_REF: Final[str] = "phase03-step7-ambiguity-persistence-v1"


class AmbiguityClass(StrEnum):
    UNRESOLVED_MAPPING = "unresolved_mapping"
    UNRESOLVED_IDENTITY = "unresolved_identity"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    COMPETING_CANONICAL_CANDIDATES = "competing_canonical_candidates"


class AmbiguityStatus(StrEnum):
    OPEN = "open"
    SUPERSEDED_BY_EVIDENCE = "superseded_by_evidence"
    SUPERSEDED_BY_MAPPING_VERSION = "superseded_by_mapping_version"
    VOID = "void"


class AmbiguityError(Exception):
    """Deterministic validation failure for ambiguity persistence."""


_ALLOWED_OPEN_CLASSES: frozenset[str] = frozenset(x.value for x in AmbiguityClass)


def _lifecycle_event(
    *,
    ambiguity_record_id: uuid.UUID,
    tenant_id: uuid.UUID,
    event_kind: str,
    previous_status: str | None,
    new_status: str,
    payload: dict[str, Any],
) -> CortexCanonicalAmbiguityLifecycleEvent:
    return CortexCanonicalAmbiguityLifecycleEvent(
        ambiguity_record_id=ambiguity_record_id,
        tenant_id=tenant_id,
        event_kind=event_kind,
        previous_status=previous_status,
        new_status=new_status,
        payload=payload,
    )


def open_ambiguity_record(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    ambiguity_class: str,
    scope: str,
    raw_record_ids: list[int],
    rule_ids_involved: list[str] | None = None,
    record_handle: str | None = None,
    evidence_payload: dict[str, Any] | None = None,
) -> CortexCanonicalAmbiguityRecord:
    if ambiguity_class not in _ALLOWED_OPEN_CLASSES:
        raise AmbiguityError(f"invalid_ambiguity_class:{ambiguity_class}")
    if not raw_record_ids:
        raise AmbiguityError("raw_record_ids_required")
    if not scope.strip():
        raise AmbiguityError("scope_required")

    bundle = db.get(CortexMappingBundle, bundle_id)
    if bundle is None:
        raise AmbiguityError("unknown_bundle")

    raw_rows = db.scalars(
        select(RawIngestionRecord).where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.id.in_(raw_record_ids),
        )
    ).all()
    if len(raw_rows) != len(set(raw_record_ids)):
        raise AmbiguityError("raw_record_ids_not_found_or_wrong_tenant")

    first = min(raw_rows, key=lambda r: r.id)
    handle = record_handle.strip() if record_handle and record_handle.strip() else None
    rec = CortexCanonicalAmbiguityRecord(
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        ambiguity_class=ambiguity_class,
        scope=scope.strip(),
        record_handle=handle,
        raw_record_ids=list(sorted(set(raw_record_ids))),
        rule_ids_involved=sorted(rule_ids_involved or []),
        primary_connector=first.connector,
        primary_resource_type=first.resource_type,
        status=AmbiguityStatus.OPEN.value,
        evidence_payload=dict(evidence_payload or {}),
        engine_build_ref=AMBIGUITY_ENGINE_BUILD_REF,
    )
    db.add(rec)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AmbiguityError("duplicate_record_handle") from exc

    db.add(
        _lifecycle_event(
            ambiguity_record_id=rec.id,
            tenant_id=tenant_id,
            event_kind="opened",
            previous_status=None,
            new_status=AmbiguityStatus.OPEN.value,
            payload={},
        )
    )
    db.commit()
    return db.scalars(
        select(CortexCanonicalAmbiguityRecord)
        .where(CortexCanonicalAmbiguityRecord.id == rec.id)
        .options(selectinload(CortexCanonicalAmbiguityRecord.lifecycle_events))
    ).one()


def _allowed_target_statuses(current: str) -> frozenset[str]:
    if current == AmbiguityStatus.OPEN.value:
        return frozenset(
            {
                AmbiguityStatus.SUPERSEDED_BY_EVIDENCE.value,
                AmbiguityStatus.SUPERSEDED_BY_MAPPING_VERSION.value,
                AmbiguityStatus.VOID.value,
            }
        )
    if current in (
        AmbiguityStatus.SUPERSEDED_BY_EVIDENCE.value,
        AmbiguityStatus.SUPERSEDED_BY_MAPPING_VERSION.value,
    ):
        return frozenset({AmbiguityStatus.VOID.value})
    return frozenset()


def transition_ambiguity_record(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    ambiguity_record_id: uuid.UUID,
    target_status: str,
    supersession_note: str | None = None,
    superseded_by_ambiguity_id: uuid.UUID | None = None,
) -> CortexCanonicalAmbiguityRecord:
    if target_status not in {x.value for x in AmbiguityStatus}:
        raise AmbiguityError(f"invalid_status:{target_status}")

    rec = db.scalars(
        select(CortexCanonicalAmbiguityRecord).where(
            CortexCanonicalAmbiguityRecord.id == ambiguity_record_id,
            CortexCanonicalAmbiguityRecord.tenant_id == tenant_id,
        )
    ).first()
    if rec is None:
        raise AmbiguityError("ambiguity_record_not_found")

    if target_status == rec.status:
        raise AmbiguityError("no_status_change")

    allowed = _allowed_target_statuses(rec.status)
    if target_status not in allowed:
        raise AmbiguityError(f"illegal_transition:{rec.status}->{target_status}")

    if superseded_by_ambiguity_id is not None:
        other = db.scalars(
            select(CortexCanonicalAmbiguityRecord).where(
                CortexCanonicalAmbiguityRecord.id == superseded_by_ambiguity_id,
                CortexCanonicalAmbiguityRecord.tenant_id == tenant_id,
            )
        ).first()
        if other is None:
            raise AmbiguityError("superseded_by_ambiguity_not_found")

    prev = rec.status
    from datetime import datetime, timezone

    rec.status = target_status
    rec.supersession_note = supersession_note
    rec.superseded_by_ambiguity_id = superseded_by_ambiguity_id
    if target_status in (
        AmbiguityStatus.SUPERSEDED_BY_EVIDENCE.value,
        AmbiguityStatus.SUPERSEDED_BY_MAPPING_VERSION.value,
        AmbiguityStatus.VOID.value,
    ):
        rec.superseded_at = datetime.now(timezone.utc)

    event_kind = target_status if target_status != AmbiguityStatus.VOID.value else "voided"
    if target_status == AmbiguityStatus.SUPERSEDED_BY_EVIDENCE.value:
        event_kind = "superseded_by_evidence"
    elif target_status == AmbiguityStatus.SUPERSEDED_BY_MAPPING_VERSION.value:
        event_kind = "superseded_by_mapping_version"

    payload: dict[str, Any] = {}
    if supersession_note:
        payload["note"] = supersession_note
    if superseded_by_ambiguity_id:
        payload["superseded_by_ambiguity_id"] = str(superseded_by_ambiguity_id)

    db.add(
        _lifecycle_event(
            ambiguity_record_id=rec.id,
            tenant_id=tenant_id,
            event_kind=event_kind,
            previous_status=prev,
            new_status=target_status,
            payload=payload,
        )
    )
    db.commit()
    return db.scalars(
        select(CortexCanonicalAmbiguityRecord)
        .where(CortexCanonicalAmbiguityRecord.id == rec.id)
        .options(selectinload(CortexCanonicalAmbiguityRecord.lifecycle_events))
    ).one()


def get_ambiguity_record(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    ambiguity_record_id: uuid.UUID,
) -> CortexCanonicalAmbiguityRecord | None:
    return db.scalars(
        select(CortexCanonicalAmbiguityRecord)
        .where(
            CortexCanonicalAmbiguityRecord.id == ambiguity_record_id,
            CortexCanonicalAmbiguityRecord.tenant_id == tenant_id,
        )
        .options(selectinload(CortexCanonicalAmbiguityRecord.lifecycle_events))
    ).first()


def list_ambiguity_records(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    status: str | None = None,
    ambiguity_class: str | None = None,
    connector: str | None = None,
    limit: int = 50,
) -> list[CortexCanonicalAmbiguityRecord]:
    lim = max(1, min(limit, 200))
    q = select(CortexCanonicalAmbiguityRecord).where(CortexCanonicalAmbiguityRecord.tenant_id == tenant_id)
    if status:
        q = q.where(CortexCanonicalAmbiguityRecord.status == status)
    if ambiguity_class:
        q = q.where(CortexCanonicalAmbiguityRecord.ambiguity_class == ambiguity_class)
    if connector:
        q = q.where(CortexCanonicalAmbiguityRecord.primary_connector == connector)
    q = q.order_by(CortexCanonicalAmbiguityRecord.created_at.desc()).limit(lim)
    return list(db.scalars(q).all())


def ambiguity_record_public_dict(
    rec: CortexCanonicalAmbiguityRecord,
    *,
    include_events: bool = False,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": rec.id,
        "tenant_id": rec.tenant_id,
        "bundle_id": rec.bundle_id,
        "ambiguity_class": rec.ambiguity_class,
        "scope": rec.scope,
        "record_handle": rec.record_handle,
        "raw_record_ids": list(rec.raw_record_ids) if isinstance(rec.raw_record_ids, list) else rec.raw_record_ids,
        "rule_ids_involved": list(rec.rule_ids_involved)
        if isinstance(rec.rule_ids_involved, list)
        else rec.rule_ids_involved,
        "primary_connector": rec.primary_connector,
        "primary_resource_type": rec.primary_resource_type,
        "status": rec.status,
        "superseded_at": rec.superseded_at,
        "supersession_note": rec.supersession_note,
        "superseded_by_ambiguity_id": rec.superseded_by_ambiguity_id,
        "evidence_payload": rec.evidence_payload,
        "engine_build_ref": rec.engine_build_ref,
        "created_at": rec.created_at,
        "updated_at": rec.updated_at,
    }
    if include_events:
        evs = sorted(rec.lifecycle_events, key=lambda e: e.id) if rec.lifecycle_events else []
        out["lifecycle_events"] = [
            {
                "id": ev.id,
                "event_kind": ev.event_kind,
                "previous_status": ev.previous_status,
                "new_status": ev.new_status,
                "payload": ev.payload,
                "created_at": ev.created_at,
            }
            for ev in evs
        ]
    return out


def build_ambiguity_aggregates(db: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    for st in AmbiguityStatus:
        c = db.scalar(
            select(func.count()).where(
                CortexCanonicalAmbiguityRecord.tenant_id == tenant_id,
                CortexCanonicalAmbiguityRecord.status == st.value,
            )
        )
        by_status[st.value] = int(c or 0)

    by_class: dict[str, int] = {}
    for cls in AmbiguityClass:
        c = db.scalar(
            select(func.count()).where(
                CortexCanonicalAmbiguityRecord.tenant_id == tenant_id,
                CortexCanonicalAmbiguityRecord.ambiguity_class == cls.value,
            )
        )
        by_class[cls.value] = int(c or 0)

    open_only = case((CortexCanonicalAmbiguityRecord.status == AmbiguityStatus.OPEN.value, 1), else_=0)
    rollup_rows = db.execute(
        select(
            CortexCanonicalAmbiguityRecord.primary_connector,
            CortexCanonicalAmbiguityRecord.primary_resource_type,
            func.count().label("total"),
            func.sum(open_only).label("open_count"),
        )
        .where(CortexCanonicalAmbiguityRecord.tenant_id == tenant_id)
        .group_by(
            CortexCanonicalAmbiguityRecord.primary_connector,
            CortexCanonicalAmbiguityRecord.primary_resource_type,
        )
    ).all()

    by_connector_resource = [
        {
            "connector": row[0] or "unknown",
            "resource_type": row[1] or "unknown",
            "total": int(row[2] or 0),
            "open_count": int(row[3] or 0),
        }
        for row in rollup_rows
    ]
    by_connector_resource.sort(key=lambda r: (-r["open_count"], r["connector"], r["resource_type"]))

    return {
        "by_status": by_status,
        "by_class": by_class,
        "by_connector_resource": by_connector_resource,
    }
