"""Phase 04 Step 18 — Execution Continuity Operator Console (HTTP §15 list-row helpers + merge-queue mutations).

Normative: ``phase-04-control-plane-doctrine.md`` §§15–16.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_org_ambiguity_record import CortexOrgAmbiguityRecord
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.domains.cortex.identity.merge_governance import get_org_merge
from vector.infrastructure.db.models.cortex_org_merge import CortexOrgMerge
from vector.infrastructure.db.models.cortex_org_primitive_instance import CortexOrgPrimitiveInstance

IDENTITY_OPERATOR_CONSOLE_SCHEMA_VERSION: Final[int] = 2
IDENTITY_OPERATOR_CONSOLE_CONFIRM_PHRASE: Final[str] = "EXECUTE IDENTITY OPERATOR CONSOLE ACTION"

IDENTITY_CONSOLE_AUDITED_POST_ACTIONS: Final[frozenset[str]] = frozenset(
    {
        "merge_queue_approve",
        "merge_queue_reject",
        "merge_queue_defer",
        "merge_queue_split",
        "org_link_revoke",
    }
)


class OperatorConsoleError(ValueError):
    """Invalid operator-console request (confirmation phrase, state, etc.)."""


def _merge_queue_pending(meta: dict[str, Any]) -> bool:
    m = dict(meta or {})
    return m.get("merge_queue_status") == "pending" or m.get("proposal_status") == "pending"


def org_handle_list_row_v1(
    session: Session,
    row: CortexOrgEntity,
    *,
    persona_touch: int = 0,
    any_candidate_touch: int = 0,
    ambiguity_touch: int = 0,
) -> dict[str, Any]:
    """§16.2 — ``org_handle_list_row_v1`` (bounded counts + candidate / ambiguity touches)."""
    meta = dict(row.metadata_json or {})
    eid = row.id
    persona_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == row.tenant_id,
                CortexOrgLink.link_type == "org.persona_belongs_to_handle",
                or_(CortexOrgLink.source_entity_id == eid, CortexOrgLink.target_entity_id == eid),
                CortexOrgLink.revoked_at.is_(None),
            )
        )
        or 0
    )
    active_links = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == row.tenant_id,
                or_(CortexOrgLink.source_entity_id == eid, CortexOrgLink.target_entity_id == eid),
                CortexOrgLink.revoked_at.is_(None),
            )
        )
        or 0
    )
    temporal_state = "tombstoned" if row.tombstoned_at else str(row.lifecycle_state or "active")
    return {
        "handle_id": str(eid),
        "kind": row.entity_kind,
        "created_from": str(meta.get("created_from") or meta.get("provenance_label") or "unknown"),
        "persona_count": persona_count,
        "active_links": active_links,
        "temporal_state": temporal_state,
        "merge_state": str(meta.get("merge_state") or "none"),
        "last_replay": str(meta.get("last_replay") or "none"),
        "confidence_posture": str(meta.get("confidence_posture") or "unknown"),
        "candidate_persona_touch_count": int(persona_touch),
        "candidate_any_touch_count": int(any_candidate_touch),
        "open_ambiguity_touch_count": int(ambiguity_touch),
        "entity_kind_rule": meta.get("entity_kind_mapping_rule_id"),
    }


def list_org_handle_list_rows(session: Session, *, tenant_id: uuid.UUID, limit: int = 100) -> list[dict[str, Any]]:
    from vector.domains.cortex.identity.anchor_continuity_candidates import (
        candidate_touch_counts,
        open_ambiguity_touch_counts,
    )

    lim = max(1, min(limit, 200))
    persona_map, total_map = candidate_touch_counts(session, tenant_id=tenant_id)
    amb_map = open_ambiguity_touch_counts(session, tenant_id=tenant_id)
    rows = list(
        session.scalars(
            select(CortexOrgEntity)
            .where(CortexOrgEntity.tenant_id == tenant_id)
            .order_by(CortexOrgEntity.created_at.desc())
            .limit(lim)
        ).all()
    )
    return [
        org_handle_list_row_v1(
            session,
            r,
            persona_touch=int(persona_map.get(r.id, 0)),
            any_candidate_touch=int(total_map.get(r.id, 0)),
            ambiguity_touch=int(amb_map.get(r.id, 0)),
        )
        for r in rows
    ]


def org_merge_queue_row_v1(session: Session, row: CortexOrgMerge) -> dict[str, Any]:
    """§16.2 — ``org_merge_queue_row_v1`` (queue metadata + bounded ambiguity touch)."""
    meta = dict(row.metadata_json or {})
    src = [uuid.UUID(str(x)) for x in (row.source_entity_ids or [])]
    tgt = row.target_entity_id
    from_handle = str(src[0]) if src else str(tgt)
    to_handle = str(tgt)
    ev = [int(x) for x in (row.evidence_raw_record_ids or [])]
    amb_n = 0
    if src or tgt:
        ent_set = set(src) | {tgt}
        for rec in session.scalars(
            select(CortexOrgAmbiguityRecord).where(
                CortexOrgAmbiguityRecord.tenant_id == row.tenant_id,
                CortexOrgAmbiguityRecord.status == "open",
            )
        ).all():
            try:
                involved = {uuid.UUID(str(x)) for x in (rec.involved_org_entity_ids or [])}
            except ValueError:
                continue
            if ent_set & involved:
                amb_n += 1
    return {
        "proposal_id": str(row.id),
        "from_handle_id": from_handle,
        "to_handle_id": to_handle,
        "evidence_sources": [str(x) for x in ev[:12]],
        "why_generated": str(meta.get("why_generated") or row.merge_kind),
        "policy_satisfied": bool(meta.get("policy_satisfied", True)),
        "candidate_age": int(meta.get("candidate_age") or 0),
        "ambiguity_count": amb_n,
        "risk_class": str(meta.get("risk_class") or "unknown"),
    }


def list_org_merge_queue_rows(session: Session, *, tenant_id: uuid.UUID, limit: int = 100) -> list[CortexOrgMerge]:
    """Merges whose metadata marks them as pending queue items (control-plane §8)."""
    lim = max(1, min(limit, 200))
    rows = list(
        session.scalars(
            select(CortexOrgMerge)
            .where(CortexOrgMerge.tenant_id == tenant_id)
            .order_by(CortexOrgMerge.created_at.desc())
            .limit(lim * 4)
        ).all()
    )
    pending = [r for r in rows if _merge_queue_pending(dict(r.metadata_json or {}))]
    return pending[:lim]


def apply_merge_queue_action(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    merge_id: uuid.UUID,
    action: str,
    confirmation_phrase: str,
    operator_note: str | None = None,
) -> CortexOrgMerge:
    """Metadata-only queue transition + durable audit row (caller commits)."""
    if (confirmation_phrase or "").strip() != IDENTITY_OPERATOR_CONSOLE_CONFIRM_PHRASE:
        raise OperatorConsoleError("confirmation_phrase_invalid")
    row = get_org_merge(session, tenant_id=tenant_id, merge_id=merge_id)
    if row is None:
        raise OperatorConsoleError("merge_proposal_not_found")
    meta = dict(row.metadata_json or {})
    if not _merge_queue_pending(meta):
        raise OperatorConsoleError("merge_queue_not_pending")
    action = (action or "").strip().lower()
    if action == "approve":
        meta["merge_queue_status"] = "approved"
        ak = "merge_queue_approve"
    elif action == "reject":
        meta["merge_queue_status"] = "rejected"
        ak = "merge_queue_reject"
    elif action == "defer":
        meta["merge_queue_status"] = "deferred"
        ak = "merge_queue_defer"
    elif action == "split":
        meta["merge_queue_status"] = "split_requested"
        ak = "merge_queue_split"
    else:
        raise OperatorConsoleError(f"unknown_merge_queue_action:{action}")
    meta["merge_queue_action_at"] = datetime.now(tz=UTC).isoformat()
    if operator_note:
        meta["operator_note"] = operator_note.strip()[:2000]
    row.metadata_json = meta
    session.flush()
    from vector.domains.cortex.identity.operator_audit import append_identity_console_audit

    append_identity_console_audit(
        session,
        tenant_id=tenant_id,
        surface="merge_queue",
        action_kind=ak,
        ref_uuid=merge_id,
        detail_json={"action": action},
    )
    return row


def org_ambiguity_queue_row_v1(rec: CortexOrgAmbiguityRecord) -> dict[str, Any]:
    """§16.2 — ``org_ambiguity_queue_row_v1``."""
    ev = dict(rec.evidence_json or {})
    raw_ids = ev.get("raw_record_ids") if isinstance(ev.get("raw_record_ids"), list) else []
    sample_ids: list[int] = []
    for x in raw_ids[:8]:
        if isinstance(x, int):
            sample_ids.append(x)
    involved = list(rec.involved_org_entity_ids or [])[:6]
    sev = str(ev.get("severity") or "medium")
    return {
        "ambiguity_id": str(rec.id),
        "class": rec.org_ambiguity_class,
        "severity": sev,
        "exemplar_handle_ids": [str(x) for x in involved],
        "evidence_sample_ids": sample_ids,
    }


def org_primitive_list_row_v1(row: CortexOrgPrimitiveInstance, *, include_raw_envelope: bool) -> dict[str, Any]:
    """§16.2 — ``org_primitive_list_row_v1`` (default list omits raw envelope — **G-P04-26**)."""
    env = dict(row.envelope_json or {})
    ev_ids = env.get("evidence_raw_record_ids")
    evc = 0
    if isinstance(ev_ids, list):
        evc = len([x for x in ev_ids if isinstance(x, int)])
    tb_from = env.get("valid_from") or env.get("temporal_from")
    tb_to = env.get("valid_to") or env.get("temporal_to")
    temporal_bounds = {"from": tb_from, "to": tb_to} if (tb_from or tb_to) else {"from": None, "to": None}
    out: dict[str, Any] = {
        "primitive_id": str(row.id),
        "primitive_kind": row.primitive_kind,
        "handle_count": 1,
        "evidence_count": evc,
        "canonical_ref_count": int(env.get("canonical_ref_count") or 0),
        "temporal_bounds": temporal_bounds,
        "replay_lineage": str(env.get("replay_lineage") or "none"),
        "export_participation": bool(env.get("export_participation", False)),
    }
    if include_raw_envelope:
        out["envelope_json"] = env
    return out
