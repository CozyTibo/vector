"""Phase 04 Step 14 — org-scoped ambiguity / multiplicity records (P04-14).

Normative: `DOCS/cortex/04-identity/phase-04-ambiguity-multiple-persona-doctrine.md`.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_org_ambiguity_record import CortexOrgAmbiguityRecord
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity

ORG_AMBIGUITY_SCHEMA_VERSION: Final[int] = 1
ORG_AMBIGUITY_ENGINE_BUILD_REF: Final[str] = "phase04-step14-org-ambiguity-v1"

ORG_AMBIGUITY_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "multiple_persona_unresolved",
        "handle_collision_unresolved",
        "cross_bundle_persona_gap",
    }
)
ORG_AMBIGUITY_STATUSES: Final[frozenset[str]] = frozenset(
    {"open", "acknowledged", "superseded", "void"},
)

# Align with canonical_verification_engine G-P03-04 bar (explosion warn).
ORG_AMBIGUITY_OPEN_WARN_THRESHOLD: Final[int] = 5000


class OrgAmbiguityError(ValueError):
    """Invalid org ambiguity append material."""


def _parse_involved_entity_ids(raw: object) -> list[uuid.UUID]:
    if not isinstance(raw, list):
        msg = "involved_org_entity_ids must be a JSON array of UUID strings"
        raise OrgAmbiguityError(msg)
    out: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    for x in raw:
        if isinstance(x, uuid.UUID):
            u = x
        elif isinstance(x, str):
            try:
                u = uuid.UUID(x.strip())
            except ValueError as exc:
                msg = f"invalid_uuid_in_involved_list:{x!r}"
                raise OrgAmbiguityError(msg) from exc
        else:
            msg = "involved_org_entity_ids entries must be UUID strings"
            raise OrgAmbiguityError(msg)
        if u not in seen:
            seen.add(u)
            out.append(u)
    if len(out) < 2:
        msg = "involved_org_entity_ids must contain at least two distinct org entities"
        raise OrgAmbiguityError(msg)
    return out


def verify_gp04_amb01_org_ambiguity_integrity_static() -> dict[str, Any]:
    """Static slice for G-P04-AMB-01 — closed class + status vocabularies."""
    errors: list[str] = []
    for c in ORG_AMBIGUITY_CLASSES:
        if not c or len(c) > 64:
            errors.append(f"bad_class_def:{c}")
    for s in ORG_AMBIGUITY_STATUSES:
        if not s:
            errors.append("empty_status")
    passed = len(errors) == 0
    return {"passed": passed, "detail": {"errors": errors}}


def list_org_ambiguity_records_invalid_entity_refs(
    db: Session, *, tenant_id: uuid.UUID, limit: int = 5_000
) -> list[uuid.UUID]:
    """Persisted violations: involved id not an org entity for this tenant."""
    lim = max(1, min(limit, 50_000))
    rows = list(
        db.scalars(
            select(CortexOrgAmbiguityRecord)
            .where(CortexOrgAmbiguityRecord.tenant_id == tenant_id)
            .order_by(CortexOrgAmbiguityRecord.created_at.desc())
            .limit(lim)
        ).all()
    )
    bad: set[uuid.UUID] = set()
    for r in rows:
        try:
            ids = _parse_involved_entity_ids(r.involved_org_entity_ids)
        except OrgAmbiguityError:
            bad.add(r.id)
            continue
        for eid in ids:
            ent = db.get(CortexOrgEntity, eid)
            if ent is None or ent.tenant_id != tenant_id:
                bad.add(r.id)
                break
    return sorted(bad, key=lambda x: str(x))


def _merge_involved_into_open_ambiguity(
    db: Session,
    row: CortexOrgAmbiguityRecord,
    *,
    tenant_id: uuid.UUID,
    org_ambiguity_class: str,
    new_ids: list[uuid.UUID],
    evidence_json: dict[str, Any] | None,
    engine_build_ref: str | None,
) -> CortexOrgAmbiguityRecord:
    if row.org_ambiguity_class.strip() != (org_ambiguity_class or "").strip():
        msg = "open_ambiguity_subject_key_class_mismatch"
        raise OrgAmbiguityError(msg)
    old_ids = _parse_involved_entity_ids(row.involved_org_entity_ids)
    merged = sorted(set(old_ids) | set(new_ids), key=str)
    if len(merged) < 2:
        msg = "involved_org_entity_ids must contain at least two distinct org entities"
        raise OrgAmbiguityError(msg)
    for eid in merged:
        ent = db.get(CortexOrgEntity, eid)
        if ent is None or ent.tenant_id != tenant_id:
            msg = "involved_org_entity_id_not_found_for_tenant"
            raise OrgAmbiguityError(msg)
    row.involved_org_entity_ids = [str(x) for x in merged]
    ev = dict(row.evidence_json or {})
    if evidence_json:
        ev.update(evidence_json)
    row.evidence_json = ev
    if engine_build_ref:
        row.engine_build_ref = engine_build_ref
    db.flush()
    return row


def append_org_ambiguity_record(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    org_ambiguity_class: str,
    subject_key: str,
    involved_org_entity_ids: list[uuid.UUID] | list[str],
    status: str = "open",
    evidence_json: dict[str, Any] | None = None,
    operator_note: str | None = None,
    engine_build_ref: str | None = None,
) -> CortexOrgAmbiguityRecord:
    cls = (org_ambiguity_class or "").strip()
    if cls not in ORG_AMBIGUITY_CLASSES:
        msg = f"org_ambiguity_class not allowed:{cls}"
        raise OrgAmbiguityError(msg)
    sk = (subject_key or "").strip()
    if not sk:
        msg = "subject_key required"
        raise OrgAmbiguityError(msg)
    st = (status or "").strip()
    if st not in ORG_AMBIGUITY_STATUSES:
        msg = f"status not allowed:{st}"
        raise OrgAmbiguityError(msg)
    ids = _parse_involved_entity_ids(list(involved_org_entity_ids))
    for eid in ids:
        ent = db.get(CortexOrgEntity, eid)
        if ent is None or ent.tenant_id != tenant_id:
            msg = "involved_org_entity_id_not_found_for_tenant"
            raise OrgAmbiguityError(msg)
    if st == "open":
        existing = db.scalars(
            select(CortexOrgAmbiguityRecord).where(
                CortexOrgAmbiguityRecord.tenant_id == tenant_id,
                CortexOrgAmbiguityRecord.subject_key == sk,
                CortexOrgAmbiguityRecord.status == "open",
            )
        ).first()
        if existing is not None:
            return _merge_involved_into_open_ambiguity(
                db,
                existing,
                tenant_id=tenant_id,
                org_ambiguity_class=cls,
                new_ids=ids,
                evidence_json=evidence_json,
                engine_build_ref=engine_build_ref or ORG_AMBIGUITY_ENGINE_BUILD_REF,
            )
    row = CortexOrgAmbiguityRecord(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        org_ambiguity_class=cls,
        subject_key=sk,
        status=st,
        involved_org_entity_ids=[str(x) for x in ids],
        evidence_json=dict(evidence_json or {}),
        operator_note=(operator_note.strip() if operator_note else None),
        engine_build_ref=engine_build_ref or ORG_AMBIGUITY_ENGINE_BUILD_REF,
    )
    db.add(row)
    db.flush()
    return row


def list_org_ambiguity_records(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 100,
    status: str | None = None,
    org_ambiguity_class: str | None = None,
) -> list[CortexOrgAmbiguityRecord]:
    lim = max(1, min(limit, 500))
    q = select(CortexOrgAmbiguityRecord).where(CortexOrgAmbiguityRecord.tenant_id == tenant_id)
    if status:
        q = q.where(CortexOrgAmbiguityRecord.status == status.strip())
    if org_ambiguity_class:
        q = q.where(CortexOrgAmbiguityRecord.org_ambiguity_class == org_ambiguity_class.strip())
    q = q.order_by(CortexOrgAmbiguityRecord.created_at.desc()).limit(lim)
    return list(db.scalars(q).all())


def get_org_ambiguity_record(
    db: Session, *, tenant_id: uuid.UUID, record_id: uuid.UUID
) -> CortexOrgAmbiguityRecord | None:
    row = db.get(CortexOrgAmbiguityRecord, record_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def org_ambiguity_record_public_dict(row: CortexOrgAmbiguityRecord) -> dict[str, Any]:
    return {
        "org_ambiguity_schema_version": ORG_AMBIGUITY_SCHEMA_VERSION,
        "id": row.id,
        "tenant_id": row.tenant_id,
        "org_ambiguity_class": row.org_ambiguity_class,
        "subject_key": row.subject_key,
        "status": row.status,
        "involved_org_entity_ids": list(row.involved_org_entity_ids or []),
        "evidence_json": dict(row.evidence_json or {}),
        "superseded_by_org_ambiguity_id": row.superseded_by_org_ambiguity_id,
        "operator_note": row.operator_note,
        "engine_build_ref": row.engine_build_ref,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def count_open_org_ambiguity_records(db: Session, *, tenant_id: uuid.UUID) -> int:
    n = db.scalar(
        select(func.count())
        .select_from(CortexOrgAmbiguityRecord)
        .where(CortexOrgAmbiguityRecord.tenant_id == tenant_id, CortexOrgAmbiguityRecord.status == "open")
    )
    return int(n or 0)
