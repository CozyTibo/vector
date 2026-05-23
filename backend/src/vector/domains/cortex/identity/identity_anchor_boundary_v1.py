"""Wave S2 — anchor → org entity boundary writes (canonical_entity_id on org rows)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import String, cast, exists, select, text
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.anchor_projection import (
    identity_material_for_anchor_backfill,
    legacy_org_handle_lane_eligible,
    provider_login_for_kind_resolution,
)
from vector.domains.cortex.identity.entity_kind_mapping import resolve_org_entity_kind_for_anchor
from vector.domains.cortex.identity.identity_primitive_projection import (
    extract_identity_primitives,
    identity_primitive_backfill_metadata,
    org_entity_id_for_identity_primitive,
    resolve_org_entity_kind_for_identity_primitive,
)
from vector.domains.cortex.identity.org_entities import (
    deterministic_org_entity_id,
    identity_key_fingerprint,
    upsert_org_entity,
)
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

IDENTITY_ANCHOR_BOUNDARY_SCHEMA_VERSION: Final[int] = 1
ORG_IDENTITY_BOUNDARY_ENGINE_BUILD_REF: Final[str] = "wave-s2-anchor-boundary-v1"


def snapshot_anchor_entity_boundary_v1(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Count anchors without a matching active org entity (plan §5.3 validation SQL)."""
    tid = str(tenant_id)
    row = session.execute(
        text(
            """
            SELECT
              (SELECT COUNT(*)::bigint FROM cortex_canonical_identity_anchors
               WHERE tenant_id = :tenant) AS anchor_count,
              (SELECT COUNT(*)::bigint FROM cortex_canonical_identity_anchors a
               WHERE a.tenant_id = :tenant
                 AND NOT EXISTS (
                   SELECT 1 FROM cortex_org_entities e
                   WHERE e.tenant_id = a.tenant_id
                     AND e.tombstoned_at IS NULL
                     AND e.metadata_json->>'canonical_entity_id' = a.canonical_entity_id::text
                 )) AS anchors_missing_entity
            """
        ),
        {"tenant": tid},
    ).mappings().first()
    anchor_count = int(row["anchor_count"] or 0) if row else 0
    missing = int(row["anchors_missing_entity"] or 0) if row else 0
    pct = round(100.0 * missing / anchor_count, 2) if anchor_count else None
    return {
        "schema_version": IDENTITY_ANCHOR_BOUNDARY_SCHEMA_VERSION,
        "tenant_id": tid,
        "anchor_count": anchor_count,
        "anchors_missing_org_entity": missing,
        "anchors_with_org_entity": max(0, anchor_count - missing),
        "anchors_missing_org_entity_pct": pct,
    }


def _upsert_org_entities_for_anchor_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    anchor: CortexCanonicalIdentityAnchor,
    raw: RawIngestionRecord | None,
    backfill_job_id: str | None = None,
) -> int:
    """Upsert org entities for one anchor (same semantics as anchor backfill)."""
    projections = extract_identity_primitives(anchor=anchor, raw=raw)
    touched = 0
    if not projections:
        if not legacy_org_handle_lane_eligible(
            canonical_object_kind=anchor.canonical_object_kind,
            raw=raw,
        ):
            return 0
        material = identity_material_for_anchor_backfill(anchor)
        login = provider_login_for_kind_resolution(anchor, raw)
        entity_kind, mapping_rule_id = resolve_org_entity_kind_for_anchor(
            connector=anchor.connector,
            canonical_object_kind=anchor.canonical_object_kind,
            resource_type=raw.resource_type if raw is not None else None,
            provider_login=login,
        )
        eid = deterministic_org_entity_id(
            tenant_id=tenant_id,
            entity_kind=entity_kind,
            fingerprint=identity_key_fingerprint(material),
        )
        existing = db.get(CortexOrgEntity, eid)
        prev_meta = dict(existing.metadata_json or {}) if existing is not None else {}
        meta = {
            **prev_meta,
            "canonical_entity_id": str(anchor.canonical_entity_id),
            "anchor_backfill_lane": "canonical_identity_anchor_v1",
            "entity_kind_mapping_rule_id": mapping_rule_id,
            "continuity_seed_strategy": "canonical_identity_anchor_v1",
            "source_anchor_ref": str(anchor.canonical_entity_id),
        }
        if backfill_job_id:
            meta["backfill_job_id"] = backfill_job_id
        upsert_org_entity(
            db,
            tenant_id=tenant_id,
            entity_kind=entity_kind,
            identity_material=material,
            metadata_json=meta,
            engine_build_ref=ORG_IDENTITY_BOUNDARY_ENGINE_BUILD_REF,
        )
        return 1

    for proj in projections:
        eid = org_entity_id_for_identity_primitive(tenant_id=tenant_id, projection=proj)
        entity_kind, _mr = resolve_org_entity_kind_for_identity_primitive(
            projection_kind=proj.projection_kind,
            github_login=proj.identity_material.get("github_login")
            if proj.projection_kind == "github_user"
            else None,
        )
        existing = db.get(CortexOrgEntity, eid)
        prev_meta = dict(existing.metadata_json or {}) if existing is not None else {}
        meta = {
            **prev_meta,
            **identity_primitive_backfill_metadata(
                anchor=anchor,
                raw=raw,
                projection=proj,
                backfill_job_id=backfill_job_id,
            ),
        }
        upsert_org_entity(
            db,
            tenant_id=tenant_id,
            entity_kind=entity_kind,
            identity_material=proj.identity_material,
            metadata_json=meta,
            engine_build_ref=ORG_IDENTITY_BOUNDARY_ENGINE_BUILD_REF,
        )
        touched += 1
    return touched


def repair_anchor_org_entity_boundary_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 5_000,
    dry_run: bool = False,
    backfill_job_id: str | None = None,
) -> dict[str, Any]:
    """Write org entity rows for anchors still missing ``metadata_json.canonical_entity_id`` match."""
    before = snapshot_anchor_entity_boundary_v1(db, tenant_id=tenant_id)
    lim = max(1, min(int(limit), 50_000))
    entity_for_anchor = exists(
        select(1)
        .select_from(CortexOrgEntity)
        .where(
            CortexOrgEntity.tenant_id == tenant_id,
            CortexOrgEntity.tombstoned_at.is_(None),
            CortexOrgEntity.metadata_json["canonical_entity_id"].astext
            == cast(CortexCanonicalIdentityAnchor.canonical_entity_id, String),
        )
    )
    missing_anchors = list(
        db.scalars(
            select(CortexCanonicalIdentityAnchor)
            .where(CortexCanonicalIdentityAnchor.tenant_id == tenant_id)
            .where(~entity_for_anchor)
            .order_by(CortexCanonicalIdentityAnchor.updated_at.desc().nullslast())
            .limit(lim)
        ).all()
    )
    entities_touched = 0
    if not dry_run:
        raw_ids = {int(a.raw_record_id) for a in missing_anchors if a.raw_record_id is not None}
        raw_by_id: dict[int, RawIngestionRecord] = {}
        if raw_ids:
            for r in db.scalars(select(RawIngestionRecord).where(RawIngestionRecord.id.in_(raw_ids))).all():
                raw_by_id[int(r.id)] = r
        for anchor in missing_anchors:
            raw = raw_by_id.get(int(anchor.raw_record_id)) if anchor.raw_record_id is not None else None
            entities_touched += _upsert_org_entities_for_anchor_v1(
                db,
                tenant_id=tenant_id,
                anchor=anchor,
                raw=raw,
                backfill_job_id=backfill_job_id,
            )
        db.flush()
    after = snapshot_anchor_entity_boundary_v1(db, tenant_id=tenant_id)
    return {
        "schema_version": IDENTITY_ANCHOR_BOUNDARY_SCHEMA_VERSION,
        "dry_run": dry_run,
        "anchors_scanned_for_repair": len(missing_anchors),
        "entities_touched": entities_touched,
        "topology_before": before,
        "topology_after": after,
        "anchors_missing_delta": int(after.get("anchors_missing_org_entity") or 0)
        - int(before.get("anchors_missing_org_entity") or 0),
    }
