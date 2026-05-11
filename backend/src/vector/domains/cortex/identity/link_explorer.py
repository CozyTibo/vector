"""Phase 04 Step 18 — link ledger explorer filters + ``org_link_list_row_v1`` rows (G-P04-22).

Normative filter keys: ``phase-04-control-plane-doctrine.md`` §9.2.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import and_, nullslast, or_, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_org_ambiguity_record import CortexOrgAmbiguityRecord
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate

LINK_EXPLORER_FILTER_KEYS: Final[frozenset[str]] = frozenset(
    {
        "authoritative_only",
        "candidate_only",
        "ambiguous",
        "revoked",
        "replay_drift",
        "rule_version",
        "primitive_id",
        "handle_id",
        "time_valid_at",
    }
)


def _norm_dt(v: datetime | None) -> datetime | None:
    if v is None:
        return None
    if v.tzinfo is None:
        return v.replace(tzinfo=UTC)
    return v


def org_link_list_row_v1_from_link(row: CortexOrgLink) -> dict[str, Any]:
    meta = dict(row.metadata_json or {})
    ev = row.evidence_raw_record_ids or []
    evc = len([x for x in ev if isinstance(x, int)])
    rid = meta.get("link_rule_version_id")
    sem = meta.get("link_rule_semantic_version") or ""
    rule_version = f"{rid}|{sem}" if rid else (sem or "")
    drift = str(meta.get("drift_class") or "NONE").upper()
    replay_state = str(meta.get("replay_state") or "clean")
    prim = meta.get("org_primitive_instance_id")
    if prim:
        target = str(prim)
        target_kind = "org_primitive"
    else:
        target = str(row.target_entity_id)
        target_kind = "org_entity"
    layer = "authoritative" if row.link_authority == "authoritative" else "non_authoritative"
    if row.link_class and row.link_class != "authoritative":
        layer = str(row.link_class)
    return {
        "link_id": str(row.id),
        "link_type": row.link_type,
        "source_handle_id": str(row.source_entity_id),
        "target": target,
        "target_kind": target_kind,
        "rule_version": rule_version,
        "link_layer": layer,
        "valid_from": row.valid_from.isoformat() if row.valid_from else None,
        "valid_to": row.valid_to.isoformat() if row.valid_to else None,
        "evidence_count": evc,
        "replay_state": replay_state,
        "drift_class": drift,
    }


def org_link_list_row_v1_from_candidate(row: CortexOrgLinkCandidate) -> dict[str, Any]:
    ev = row.evidence_raw_record_ids or []
    evc = len([x for x in ev if isinstance(x, int)])
    return {
        "link_id": str(row.id),
        "link_type": row.link_type,
        "source_handle_id": str(row.source_entity_id),
        "target": str(row.target_entity_id),
        "target_kind": "org_entity",
        "rule_version": (row.rule_id or "") + "|candidate",
        "link_layer": "candidate",
        "valid_from": None,
        "valid_to": None,
        "evidence_count": evc,
        "replay_state": "pending_regen",
        "drift_class": "NONE",
    }


def _open_ambiguity_entity_ids(session: Session, *, tenant_id: uuid.UUID) -> set[uuid.UUID]:
    rows = list(
        session.scalars(
            select(CortexOrgAmbiguityRecord).where(
                CortexOrgAmbiguityRecord.tenant_id == tenant_id,
                CortexOrgAmbiguityRecord.status == "open",
            )
        ).all()
    )
    out: set[uuid.UUID] = set()
    for r in rows:
        raw = r.involved_org_entity_ids or []
        for x in raw:
            try:
                out.add(uuid.UUID(str(x)))
            except ValueError:
                continue
    return out


def list_org_link_explorer_rows(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 100,
    authoritative_only: bool | None = None,
    candidate_only: bool | None = None,
    ambiguous: bool | None = None,
    revoked: bool | None = None,
    replay_drift: bool | None = None,
    rule_version: str | None = None,
    primitive_id: uuid.UUID | None = None,
    handle_id: uuid.UUID | None = None,
    time_valid_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """Return ``org_link_list_row_v1`` rows honoring §9.2 filters (AND semantics)."""
    if authoritative_only and candidate_only:
        raise ValueError("link_explorer_unsupported_filter_combo:authoritative_only+candidate_only")
    lim = max(1, min(limit, 200))
    tv = _norm_dt(time_valid_at)

    if candidate_only:
        stmt = select(CortexOrgLinkCandidate).where(CortexOrgLinkCandidate.tenant_id == tenant_id)
        if handle_id is not None:
            hid = handle_id
            stmt = stmt.where(
                or_(
                    CortexOrgLinkCandidate.source_entity_id == hid,
                    CortexOrgLinkCandidate.target_entity_id == hid,
                )
            )
        if rule_version:
            stmt = stmt.where(CortexOrgLinkCandidate.rule_id == rule_version.strip())
        cands = list(
            session.scalars(stmt.order_by(nullslast(CortexOrgLinkCandidate.created_at.desc())).limit(lim)).all()
        )
        return [org_link_list_row_v1_from_candidate(c) for c in cands]

    stmt = select(CortexOrgLink).where(CortexOrgLink.tenant_id == tenant_id)
    if authoritative_only:
        stmt = stmt.where(CortexOrgLink.link_authority == "authoritative")
    if revoked is True:
        stmt = stmt.where(or_(CortexOrgLink.revoked_at.is_not(None), CortexOrgLink.supersedes_link_id.is_not(None)))
    elif revoked is False:
        stmt = stmt.where(CortexOrgLink.revoked_at.is_(None), CortexOrgLink.supersedes_link_id.is_(None))
    if rule_version:
        rv = rule_version.strip()
        stmt = stmt.where(
            or_(
                CortexOrgLink.metadata_json["link_rule_version_id"].astext == rv,
                CortexOrgLink.rule_id == rv,
            )
        )
    if primitive_id is not None:
        pid = str(primitive_id)
        stmt = stmt.where(CortexOrgLink.metadata_json["org_primitive_instance_id"].astext == pid)
    if handle_id is not None:
        hid = handle_id
        stmt = stmt.where(
            or_(CortexOrgLink.source_entity_id == hid, CortexOrgLink.target_entity_id == hid),
        )
    if ambiguous:
        ent_ids = _open_ambiguity_entity_ids(session, tenant_id=tenant_id)
        if not ent_ids:
            return []
        stmt = stmt.where(
            or_(CortexOrgLink.source_entity_id.in_(ent_ids), CortexOrgLink.target_entity_id.in_(ent_ids)),
        )
    if tv is not None:
        # Point-in-time: include links whose validity interval covers ``tv``.
        stmt = stmt.where(
            or_(CortexOrgLink.valid_from.is_(None), CortexOrgLink.valid_from <= tv),
            or_(CortexOrgLink.valid_to.is_(None), CortexOrgLink.valid_to > tv),
        )

    rows = list(
        session.scalars(stmt.order_by(nullslast(CortexOrgLink.created_at.desc()), CortexOrgLink.id.asc()).limit(lim)).all()
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        if replay_drift:
            meta = dict(r.metadata_json or {})
            dc = str(meta.get("drift_class") or "NONE").upper()
            if dc in ("", "NONE"):
                continue
        out.append(org_link_list_row_v1_from_link(r))
    return out
