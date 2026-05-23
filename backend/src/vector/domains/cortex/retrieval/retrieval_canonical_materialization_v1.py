"""Wave S3 — materialize canonical transform rows into retrieval index (execution substrate)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import select
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


def _canonical_entity_ids_for_island_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    island: frozenset[uuid.UUID],
) -> set[str]:
    ids: set[str] = set()
    if not island:
        return ids
    for row in session.scalars(
        select(CortexOrgEntity).where(
            CortexOrgEntity.tenant_id == tenant_id,
            CortexOrgEntity.id.in_(island),
            CortexOrgEntity.tombstoned_at.is_(None),
        )
    ).all():
        meta = dict(row.metadata_json or {})
        raw = meta.get("canonical_entity_id")
        if raw is not None and str(raw).strip():
            ids.add(str(raw).strip())
    return ids


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
        get_retrieval_max_canonical_materializations_per_epoch_v1()
    )
    cap = max(1, min(int(cap), 5_000))
    canon_ids = _canonical_entity_ids_for_island_v1(session, tenant_id=tenant_id, island=island)
    if not canon_ids:
        return {
            "materialized_count": 0,
            "candidates": 0,
            "canonical_entity_ids_in_island": 0,
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
        "skipped": skip_reasons,
    }
