"""Phase 04 Step 20 — canonical identity anchors → org entities (candidate lane only, P04-20).

Normative: `DOCS/cortex/04-identity/phase-04-backfill-doctrine.md`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import BigInteger, cast, nullslast, or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.anchor_projection import (
    ANCHOR_BACKFILL_LANE,
    identity_material_for_anchor_backfill,
    legacy_org_handle_lane_eligible,
    provider_login_for_kind_resolution,
)
from vector.domains.cortex.identity.entity_kind_mapping import resolve_org_entity_kind_for_anchor
from vector.domains.cortex.identity.identity_primitive_projection import (
    IDENTITY_PRIMITIVE_LANE,
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
from vector.infrastructure.db.models.cortex_org_identity_backfill_run import CortexOrgIdentityBackfillRun
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

ORG_IDENTITY_BACKFILL_SCHEMA_VERSION: Final[int] = 3
ORG_IDENTITY_BACKFILL_ENGINE_BUILD_REF: Final[str] = "phase04-step20-identity-primitive-backfill-v1"


def tombstone_legacy_anchor_org_entities_superseded_by_primitives(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    anchors: list[CortexCanonicalIdentityAnchor],
) -> int:
    """Soft-delete legacy per-anchor org rows when primitive projection now owns the same raw anchor.

    Prevents duplicate active org handles (legacy lane + primitive lane) for the same anchor.
    """
    prim_raw: set[int] = set()
    for anchor in anchors:
        if anchor.raw_record_id is None:
            continue
        raw = db.get(RawIngestionRecord, int(anchor.raw_record_id))
        if extract_identity_primitives(anchor=anchor, raw=raw):
            prim_raw.add(int(anchor.raw_record_id))
    if not prim_raw:
        return 0
    rid_expr = cast(CortexOrgEntity.metadata_json["source_anchor_raw_record_id"].astext, BigInteger)
    stmt = select(CortexOrgEntity).where(
        CortexOrgEntity.tenant_id == tenant_id,
        CortexOrgEntity.tombstoned_at.is_(None),
        CortexOrgEntity.metadata_json["anchor_backfill_lane"].astext == ANCHOR_BACKFILL_LANE,
        rid_expr.in_(sorted(prim_raw)),
    )
    rows = list(db.scalars(stmt).all())
    now = datetime.now(UTC)
    for row in rows:
        row.tombstoned_at = now
        meta = dict(row.metadata_json or {})
        meta["tombstone_reason"] = "superseded_by_identity_primitive_backfill"
        row.metadata_json = meta
    if rows:
        db.flush()
    return len(rows)


def compute_anchor_backfill_set_sha256(anchors: list[CortexCanonicalIdentityAnchor]) -> str:
    """Deterministic hash over scanned anchors (canonical id + provider hash)."""
    parts = [f"{a.canonical_entity_id}|{a.provider_identity_hash}" for a in anchors]
    parts.sort()
    blob = json.dumps(parts, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def list_identity_anchors_for_backfill(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int = 0,
) -> list[CortexCanonicalIdentityAnchor]:
    lim = max(1, min(int(limit), 50_000))
    off = max(0, int(offset))
    return list(
        db.scalars(
            select(CortexCanonicalIdentityAnchor)
            .where(CortexCanonicalIdentityAnchor.tenant_id == tenant_id)
            .order_by(nullslast(CortexCanonicalIdentityAnchor.updated_at.desc()))
            .offset(off)
            .limit(lim)
        ).all()
    )


def run_anchor_handle_backfill(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    dry_run: bool = False,
    anchor_limit: int = 5_000,
    anchor_offset: int = 0,
    skip_candidate_regen: bool = False,
) -> dict[str, Any]:
    """Upsert org entities from anchors; never writes authoritative org links (P04-20)."""
    anchors = list_identity_anchors_for_backfill(
        db, tenant_id=tenant_id, limit=anchor_limit, offset=anchor_offset
    )
    set_sha = compute_anchor_backfill_set_sha256(anchors)
    legacy_lane_org_entities_tombstoned = 0
    anchors_skipped_work_object_no_primitive = 0
    run_row: CortexOrgIdentityBackfillRun | None = None
    run_id: str | None = None
    if not dry_run:
        run_row = CortexOrgIdentityBackfillRun(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            dry_run=False,
            anchors_scanned=0,
            entities_upserted=0,
            backfill_set_sha256=set_sha,
            summary_json={
                "org_identity_backfill_schema_version": ORG_IDENTITY_BACKFILL_SCHEMA_VERSION,
                "status": "running",
                "anchor_limit_applied": anchor_limit,
            },
            engine_build_ref=ORG_IDENTITY_BACKFILL_ENGINE_BUILD_REF,
        )
        db.add(run_row)
        db.flush()
        run_id = str(run_row.id)

    if not dry_run:
        legacy_lane_org_entities_tombstoned = tombstone_legacy_anchor_org_entities_superseded_by_primitives(
            db, tenant_id=tenant_id, anchors=anchors
        )

    upserted = 0
    for anchor in anchors:
        raw = db.get(RawIngestionRecord, int(anchor.raw_record_id)) if anchor.raw_record_id is not None else None
        projections = extract_identity_primitives(anchor=anchor, raw=raw)
        if dry_run:
            if projections:
                upserted += len(projections)
            elif legacy_org_handle_lane_eligible(
                canonical_object_kind=anchor.canonical_object_kind,
                raw=raw,
            ):
                upserted += 1
            else:
                anchors_skipped_work_object_no_primitive += 1
            continue
        if not projections:
            if not legacy_org_handle_lane_eligible(
                canonical_object_kind=anchor.canonical_object_kind,
                raw=raw,
            ):
                anchors_skipped_work_object_no_primitive += 1
                continue
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
                "anchor_backfill_lane": ANCHOR_BACKFILL_LANE,
                "canonical_entity_id": str(anchor.canonical_entity_id),
                "source_anchor_raw_record_id": int(anchor.raw_record_id),
                "source_anchor_connector": anchor.connector,
                "source_anchor_bundle_id": anchor.bundle_id,
                "created_from": f"{anchor.connector}:{anchor.canonical_object_kind}",
                "provenance_label": f"anchor:{anchor.canonical_entity_id}",
                "source_connector": anchor.connector,
                "source_anchor_type": anchor.canonical_object_kind,
                "source_anchor_ref": str(anchor.canonical_entity_id),
                "continuity_seed_strategy": ANCHOR_BACKFILL_LANE,
                "entity_kind_mapping_rule_id": mapping_rule_id,
            }
            if run_id is not None:
                meta["backfill_job_id"] = run_id
            upsert_org_entity(
                db,
                tenant_id=tenant_id,
                entity_kind=entity_kind,
                identity_material=material,
                metadata_json=meta,
                engine_build_ref=ORG_IDENTITY_BACKFILL_ENGINE_BUILD_REF,
            )
            upserted += 1
            continue
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
                    backfill_job_id=run_id,
                ),
            }
            upsert_org_entity(
                db,
                tenant_id=tenant_id,
                entity_kind=entity_kind,
                identity_material=proj.identity_material,
                metadata_json=meta,
                engine_build_ref=ORG_IDENTITY_BACKFILL_ENGINE_BUILD_REF,
            )
            upserted += 1

    if run_row is not None:
        run_row.anchors_scanned = len(anchors)
        run_row.entities_upserted = upserted
        run_row.summary_json = {
            **dict(run_row.summary_json or {}),
            "status": "completed",
            "dry_run": False,
            "org_identity_backfill_schema_version": ORG_IDENTITY_BACKFILL_SCHEMA_VERSION,
            "anchor_limit_applied": anchor_limit,
            "legacy_lane_org_entities_tombstoned": legacy_lane_org_entities_tombstoned,
            "anchors_skipped_work_object_no_primitive": anchors_skipped_work_object_no_primitive,
        }
        db.flush()

    regen: dict[str, Any] | None = None
    boundary: dict[str, Any] | None = None
    if not dry_run:
        from vector.domains.cortex.identity.identity_anchor_boundary_v1 import (
            repair_anchor_org_entity_boundary_v1,
        )

        boundary = repair_anchor_org_entity_boundary_v1(
            db,
            tenant_id=tenant_id,
            limit=anchor_limit,
            dry_run=False,
            backfill_job_id=run_id,
        )

    regen: dict[str, Any] | None = None
    if not dry_run and not skip_candidate_regen:
        from vector.domains.cortex.identity.anchor_continuity_candidates import (
            run_anchor_continuity_candidate_regeneration,
        )

        regen = run_anchor_continuity_candidate_regeneration(db, tenant_id=tenant_id)

    return {
        "org_identity_backfill_schema_version": ORG_IDENTITY_BACKFILL_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "dry_run": dry_run,
        "anchors_scanned": len(anchors),
        "entities_upserted": upserted,
        "backfill_set_sha256": set_sha,
        "run_id": run_id,
        "engine_build_ref": ORG_IDENTITY_BACKFILL_ENGINE_BUILD_REF,
        "legacy_lane_org_entities_tombstoned": legacy_lane_org_entities_tombstoned,
        "anchors_skipped_work_object_no_primitive": anchors_skipped_work_object_no_primitive,
        "candidate_regeneration": regen,
        "anchor_entity_boundary": boundary,
    }


def org_identity_backfill_run_public_dict(row: CortexOrgIdentityBackfillRun) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "dry_run": bool(row.dry_run),
        "anchors_scanned": int(row.anchors_scanned),
        "entities_upserted": int(row.entities_upserted),
        "backfill_set_sha256": row.backfill_set_sha256,
        "summary_json": dict(row.summary_json or {}),
        "engine_build_ref": row.engine_build_ref,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_org_identity_backfill_runs(db: Session, *, tenant_id: uuid.UUID, limit: int = 20) -> list[CortexOrgIdentityBackfillRun]:
    lim = max(1, min(int(limit), 100))
    return list(
        db.scalars(
            select(CortexOrgIdentityBackfillRun)
            .where(CortexOrgIdentityBackfillRun.tenant_id == tenant_id)
            .order_by(CortexOrgIdentityBackfillRun.created_at.desc())
            .limit(lim)
        ).all()
    )


def verify_gp04_bf01_no_authoritative_links_on_backfill_handles(
    session: Session, *, tenant_id: uuid.UUID
) -> dict[str, Any]:
    """G-P04-BF-01 — backfill-lane org handles must not participate in authoritative org links."""
    ids = list(
        session.scalars(
            select(CortexOrgEntity.id).where(
                CortexOrgEntity.tenant_id == tenant_id,
                or_(
                    CortexOrgEntity.metadata_json["anchor_backfill_lane"].astext == ANCHOR_BACKFILL_LANE,
                    CortexOrgEntity.metadata_json["anchor_backfill_lane"].astext == IDENTITY_PRIMITIVE_LANE,
                ),
            )
        ).all()
    )
    if not ids:
        return {
            "id": "G-P04-BF-01",
            "name": "anchor_backfill_no_authoritative_org_links",
            "passed": True,
            "severity": "hard_fail",
            "detail": {
                "tenant_id": str(tenant_id),
                "backfill_org_entity_count": 0,
                "violating_link_count": 0,
            },
        }

    bad = list(
        session.scalars(
            select(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_authority == "authoritative",
                CortexOrgLink.revoked_at.is_(None),
                or_(CortexOrgLink.source_entity_id.in_(ids), CortexOrgLink.target_entity_id.in_(ids)),
            )
            .limit(200)
        ).all()
    )
    return {
        "id": "G-P04-BF-01",
        "name": "anchor_backfill_no_authoritative_org_links",
        "passed": len(bad) == 0,
        "severity": "hard_fail",
        "detail": {
            "tenant_id": str(tenant_id),
            "backfill_org_entity_count": len(ids),
            "violating_link_count": len(bad),
            "sample_link_ids": [str(x.id) for x in bad[:20]],
        },
    }
