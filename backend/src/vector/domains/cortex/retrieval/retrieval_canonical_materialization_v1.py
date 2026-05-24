"""Wave S3 — materialize canonical transform rows into retrieval index (execution substrate)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    materialize_retrieval_index_entry_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_projection import RetrievalLegalityError
from vector.domains.cortex.retrieval.retrieval_materialization_caps_v1 import (
    get_retrieval_max_canonical_materializations_per_epoch_v1,
)
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import (
    CortexCanonicalIdentityAnchor,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity

RETRIEVAL_CANONICAL_MATERIALIZATION_SCHEMA_VERSION: Final[int] = 1
ISLAND_CANONICAL_BINDING_METADATA_KEYS_V1: Final[tuple[str, ...]] = (
    "canonical_entity_id",
    "source_anchor_ref",
)
ANCHOR_ORG_ENTITY_FALLBACK_SCAN_LIMIT_V1: Final[int] = 2_000


def get_retrieval_max_canonical_materializations_for_island_v1(*, island_entity_count: int) -> int:
    """Island-scoped cap: scale with component size without unbounded org_link-style mirroring."""
    base = get_retrieval_max_canonical_materializations_per_epoch_v1()
    if island_entity_count <= 0:
        return base
    boosted = min(5_000, max(base, island_entity_count * 20))
    return boosted


def _deterministic_org_entity_id_for_anchor_lane_v1(
    *,
    tenant_id: uuid.UUID,
    anchor: CortexCanonicalIdentityAnchor,
) -> uuid.UUID | None:
    """Best-effort org entity id for single-lane anchors (matches identity boundary writes)."""
    from vector.domains.cortex.identity.anchor_projection import (
        identity_material_for_anchor_backfill,
        legacy_org_handle_lane_eligible,
        provider_login_for_kind_resolution,
    )
    from vector.domains.cortex.identity.entity_kind_mapping import resolve_org_entity_kind_for_anchor
    from vector.domains.cortex.identity.org_entities import (
        deterministic_org_entity_id,
        identity_key_fingerprint,
    )

    if not legacy_org_handle_lane_eligible(
        canonical_object_kind=anchor.canonical_object_kind,
        raw=None,
    ):
        return None
    material = identity_material_for_anchor_backfill(anchor)
    login = provider_login_for_kind_resolution(anchor, None)
    entity_kind, _rule = resolve_org_entity_kind_for_anchor(
        connector=anchor.connector,
        canonical_object_kind=anchor.canonical_object_kind,
        resource_type=None,
        provider_login=login,
    )
    return deterministic_org_entity_id(
        tenant_id=tenant_id,
        entity_kind=entity_kind,
        fingerprint=identity_key_fingerprint(material),
    )


def _canonical_entity_ids_for_island_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    island: frozenset[uuid.UUID],
) -> tuple[set[str], dict[str, int]]:
    ids: set[str] = set()
    stats = {
        "island_org_entities": len(island),
        "from_org_metadata": 0,
        "from_anchor_join": 0,
        "from_anchor_org_entity_fallback": 0,
    }
    if not island:
        return ids, stats

    island_list = [str(eid) for eid in island]
    for row in session.scalars(
        select(CortexOrgEntity).where(
            CortexOrgEntity.tenant_id == tenant_id,
            CortexOrgEntity.id.in_(island),
            CortexOrgEntity.tombstoned_at.is_(None),
        )
    ).all():
        meta = dict(row.metadata_json or {})
        for key in ISLAND_CANONICAL_BINDING_METADATA_KEYS_V1:
            raw = meta.get(key)
            if raw is not None and str(raw).strip():
                ids.add(str(raw).strip())
                stats["from_org_metadata"] += 1
                break

    join_rows = session.execute(
        text(
            """
            SELECT DISTINCT a.canonical_entity_id::text AS cid
            FROM cortex_canonical_identity_anchors a
            INNER JOIN cortex_org_entities e
              ON e.tenant_id = a.tenant_id
             AND e.tombstoned_at IS NULL
             AND e.id = ANY(CAST(:island_ids AS uuid[]))
             AND (
               e.metadata_json->>'canonical_entity_id' = a.canonical_entity_id::text
               OR e.metadata_json->>'source_anchor_ref' = a.canonical_entity_id::text
             )
            WHERE a.tenant_id = CAST(:tenant AS uuid)
            """
        ),
        {"tenant": str(tenant_id), "island_ids": island_list},
    ).mappings()
    before_join = len(ids)
    for row in join_rows:
        cid = str(row["cid"] or "").strip()
        if cid:
            ids.add(cid)
    stats["from_anchor_join"] = max(0, len(ids) - before_join)

    if len(ids) < len(island):
        bare_island = set(island)
        scanned = 0
        for anchor in session.scalars(
            select(CortexCanonicalIdentityAnchor)
            .where(CortexCanonicalIdentityAnchor.tenant_id == tenant_id)
            .order_by(CortexCanonicalIdentityAnchor.updated_at.desc().nullslast())
            .limit(ANCHOR_ORG_ENTITY_FALLBACK_SCAN_LIMIT_V1)
        ).all():
            scanned += 1
            org_eid = _deterministic_org_entity_id_for_anchor_lane_v1(
                tenant_id=tenant_id,
                anchor=anchor,
            )
            if org_eid is not None and org_eid in bare_island:
                cid = str(anchor.canonical_entity_id)
                if cid not in ids:
                    ids.add(cid)
                    stats["from_anchor_org_entity_fallback"] += 1
        stats["anchor_fallback_scan_count"] = scanned

    return ids, stats


def materialize_canonical_materializations_for_island_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    island: frozenset[uuid.UUID],
    replay_identity: str,
    index_epoch: str,
    omission_summary: dict[str, Any] | None = None,
    max_materializations: int | None = None,
) -> dict[str, Any]:
    """Index canonical mats tied to island org entities via ``canonical_entity_id`` boundary."""
    cap = max_materializations if max_materializations is not None else (
        get_retrieval_max_canonical_materializations_for_island_v1(
            island_entity_count=len(island),
        )
    )
    cap = max(1, min(int(cap), 5_000))
    canon_ids, binding_stats = _canonical_entity_ids_for_island_v1(
        session, tenant_id=tenant_id, island=island
    )
    if not canon_ids:
        return {
            "materialized_count": 0,
            "candidates": 0,
            "canonical_entity_ids_in_island": 0,
            "island_canonical_binding": binding_stats,
            "max_materializations_cap": cap,
        }

    canon_uuids = []
    for cid in sorted(canon_ids):
        try:
            canon_uuids.append(uuid.UUID(cid))
        except ValueError:
            continue

    anchor_raw_ids: set[int] = set()
    for anchor in session.scalars(
        select(CortexCanonicalIdentityAnchor).where(
            CortexCanonicalIdentityAnchor.tenant_id == tenant_id,
            CortexCanonicalIdentityAnchor.canonical_entity_id.in_(canon_uuids),
        )
    ).all():
        anchor_raw_ids.add(int(anchor.raw_record_id))

    if not anchor_raw_ids:
        return {
            "materialized_count": 0,
            "candidates": 0,
            "canonical_entity_ids_in_island": len(canon_ids),
            "island_canonical_binding": binding_stats,
            "max_materializations_cap": cap,
        }

    mats = list(
        session.scalars(
            select(CortexCanonicalTransformMaterialization)
            .where(
                CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
                CortexCanonicalTransformMaterialization.raw_record_id.in_(anchor_raw_ids),
            )
            .order_by(
                CortexCanonicalTransformMaterialization.canonical_processed_at.desc().nullslast(),
                CortexCanonicalTransformMaterialization.created_at.desc(),
            )
            .limit(cap)
        ).all()
    )

    materialized = 0
    skip_reasons: list[dict[str, str]] = []
    omit = dict(omission_summary or {})
    for mat in mats:
        try:
            materialize_retrieval_index_entry_v1(
                session,
                tenant_id=tenant_id,
                replay_identity=replay_identity,
                index_epoch=index_epoch,
                index_kind="materialization",
                index_key=f"materialization:{mat.id}",
                chronology_legality_class="strict",
                causal_legality_class="verified",
                artifact_ref={
                    "materialization_id": str(mat.id),
                    "canonical_object_kind": mat.canonical_object_kind,
                    "raw_record_id": int(mat.raw_record_id),
                },
                omission_summary=omit,
                auto_publish=False,
            )
            materialized += 1
        except RetrievalLegalityError as exc:
            skip_reasons.append(
                {"materialization_id": str(mat.id), "code": str(exc)},
            )

    return {
        "schema_version": RETRIEVAL_CANONICAL_MATERIALIZATION_SCHEMA_VERSION,
        "materialized_count": materialized,
        "candidates": len(mats),
        "canonical_entity_ids_in_island": len(canon_ids),
        "island_canonical_binding": binding_stats,
        "max_materializations_cap": cap,
        "skipped": skip_reasons,
    }
