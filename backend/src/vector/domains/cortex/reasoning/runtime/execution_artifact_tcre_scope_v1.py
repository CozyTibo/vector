"""Phase S2.3 — TCRE materialization scope bound to execution artifacts + walk starts."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import nullslast, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.anchor_projection import org_entity_id_for_anchor_row
from vector.domains.cortex.reasoning.runtime.octs_binding_projection import resolve_octs_walk_payload_v1
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

EXECUTION_MATERIALIZATION_OBJECT_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "pull_request",
        "deployment",
        "message",
        "timeline_mutation",
        "workflow_run",
        "issue",
        "commit",
    }
)


def resolve_walk_start_node_ids_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    octs_walk_id: str | None,
) -> list[str]:
    """Start org-entity node ids from a completed OCTS walk payload."""
    payload = resolve_octs_walk_payload_v1(tenant_id, octs_walk_id=octs_walk_id, session=session)
    if not payload:
        return []
    walk_result = payload.get("walk_result") or {}
    hash_body = walk_result.get("hash_body") if isinstance(walk_result, dict) else {}
    if not isinstance(hash_body, dict):
        return []
    starts = hash_body.get("start_node_ids")
    if not isinstance(starts, list):
        return []
    return sorted({str(s).strip() for s in starts if str(s).strip()})


def filter_materializations_for_execution_artifact_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    materializations: list[CortexCanonicalTransformMaterialization],
    walk_start_node_ids: list[str] | None,
) -> tuple[list[CortexCanonicalTransformMaterialization], dict[str, Any]]:
    """Keep execution-bearing mats; when walk starts present, prefer mats anchored on those entities."""
    start_ids = {str(x) for x in (walk_start_node_ids or []) if str(x).strip()}
    raw_ids = {int(m.raw_record_id) for m in materializations}
    raw_by_id: dict[int, RawIngestionRecord] = {}
    if raw_ids:
        for raw in session.scalars(
            select(RawIngestionRecord).where(RawIngestionRecord.id.in_(raw_ids))
        ).all():
            raw_by_id[int(raw.id)] = raw

    anchor_by_raw: dict[int, CortexCanonicalIdentityAnchor] = {}
    if raw_ids:
        for anchor in session.scalars(
            select(CortexCanonicalIdentityAnchor).where(
                CortexCanonicalIdentityAnchor.tenant_id == tenant_id,
                CortexCanonicalIdentityAnchor.raw_record_id.in_(raw_ids),
            )
        ).all():
            anchor_by_raw[int(anchor.raw_record_id)] = anchor

    scoped: list[CortexCanonicalTransformMaterialization] = []
    for mat in materializations:
        kind = (mat.canonical_object_kind or "").strip()
        if kind not in EXECUTION_MATERIALIZATION_OBJECT_KINDS_V1:
            continue
        if not start_ids:
            scoped.append(mat)
            continue
        anchor = anchor_by_raw.get(int(mat.raw_record_id))
        if anchor is None:
            scoped.append(mat)
            continue
        raw = raw_by_id.get(int(mat.raw_record_id))
        eid = str(org_entity_id_for_anchor_row(tenant_id=tenant_id, anchor=anchor, raw=raw))
        if eid in start_ids:
            scoped.append(mat)

    meta = {
        "execution_artifact_scope_v1": True,
        "mat_scope_count": len(scoped),
        "mat_candidates_before_scope": len(materializations),
        "walk_start_node_count": len(start_ids),
        "execution_object_kinds": sorted(EXECUTION_MATERIALIZATION_OBJECT_KINDS_V1),
    }
    return scoped, meta


def org_entity_ids_for_execution_materializations_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 32,
) -> list[str]:
    """Org entities incident to execution-bearing canonical materializations (S2.5 walk starts)."""
    lim = max(1, min(int(limit), 128))
    mats = list(
        session.scalars(
            select(CortexCanonicalTransformMaterialization)
            .where(
                CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
                CortexCanonicalTransformMaterialization.canonical_object_kind.in_(
                    tuple(EXECUTION_MATERIALIZATION_OBJECT_KINDS_V1)
                ),
            )
            .order_by(
                nullslast(CortexCanonicalTransformMaterialization.temporal_ordering_key.asc()),
                CortexCanonicalTransformMaterialization.id.asc(),
            )
            .limit(lim * 4)
        ).all()
    )
    if not mats:
        return []

    raw_ids = {int(m.raw_record_id) for m in mats}
    raw_by_id = {
        int(r.id): r
        for r in session.scalars(select(RawIngestionRecord).where(RawIngestionRecord.id.in_(raw_ids))).all()
    }
    entity_ids: set[str] = set()
    for mat in mats:
        if len(entity_ids) >= lim:
            break
        for anchor in session.scalars(
            select(CortexCanonicalIdentityAnchor).where(
                CortexCanonicalIdentityAnchor.tenant_id == tenant_id,
                CortexCanonicalIdentityAnchor.raw_record_id == int(mat.raw_record_id),
            )
        ).all():
            raw = raw_by_id.get(int(mat.raw_record_id))
            entity_ids.add(str(org_entity_id_for_anchor_row(tenant_id=tenant_id, anchor=anchor, raw=raw)))
            if len(entity_ids) >= lim:
                break
    return sorted(entity_ids)[:lim]
