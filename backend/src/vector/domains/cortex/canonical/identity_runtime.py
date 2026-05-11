"""Phase 03 Step 9 — provider-scoped canonical identity + Phase 04 boundary hooks.

Normative: `DOCS/cortex/03-canonical/phase-03-identity-continuity-doctrine.md`.
Human/org linkage merge authority remains Phase 04+; anchors carry explicit non-merge handoff metadata.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)


def _canonical_json_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()

IDENTITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1
IDENTITY_ENGINE_BUILD_REF: Final[str] = "phase03-step9-identity-continuity-v1"

_LOGICAL_KEY_SCOPE_KEYS: Final[frozenset[str]] = frozenset({"tenant_id", "mapping_bundle_id"})

# Deterministic namespace for UUIDv5 canonical_entity_id strings (stable across processes).
PHASE03_CANONICAL_ENTITY_NAMESPACE: Final[uuid.UUID] = uuid.uuid5(
    uuid.NAMESPACE_DNS,
    "vector.phase03.canonical_identity_entity.v1",
)

DEFAULT_PHASE04_BOUNDARY: Final[dict[str, Any]] = {
    "handoff_version": 1,
    "human_identity_resolution": "phase_04_only",
    "organizational_identity_resolution": "phase_04_plus",
    "hint_edges_default": "omit",
    "linkage_merge_authority": "none",
}


def provider_identity_from_logical_key(logical_key_json: dict[str, Any]) -> dict[str, Any]:
    """Provider-scoped discriminant: logical key minus tenant/bundle scope keys (deterministic sort)."""
    return {k: logical_key_json[k] for k in sorted(logical_key_json.keys()) if k not in _LOGICAL_KEY_SCOPE_KEYS}


def deterministic_canonical_entity_id(
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    canonical_object_kind: str,
    provider_identity_hash: str,
) -> uuid.UUID:
    name = f"{tenant_id}:{bundle_id}:{canonical_object_kind}:{provider_identity_hash}"
    return uuid.uuid5(PHASE03_CANONICAL_ENTITY_NAMESPACE, name)


def canonical_entity_id_for_materialization(mat: CortexCanonicalTransformMaterialization) -> uuid.UUID:
    prof = provider_identity_from_logical_key(dict(mat.logical_key_json))
    pid_hash = _canonical_json_hash(prof)
    return deterministic_canonical_entity_id(
        tenant_id=mat.tenant_id,
        bundle_id=mat.bundle_id,
        canonical_object_kind=mat.canonical_object_kind,
        provider_identity_hash=pid_hash,
    )


def upsert_identity_anchor_for_materialization(
    db: Session,
    mat: CortexCanonicalTransformMaterialization,
    *,
    connector: str,
) -> uuid.UUID:
    """Persist or refresh identity anchor after a successful materialization (same txn)."""
    prof = provider_identity_from_logical_key(dict(mat.logical_key_json))
    pid_hash = _canonical_json_hash(prof)
    entity_id = deterministic_canonical_entity_id(
        tenant_id=mat.tenant_id,
        bundle_id=mat.bundle_id,
        canonical_object_kind=mat.canonical_object_kind,
        provider_identity_hash=pid_hash,
    )
    row = db.get(CortexCanonicalIdentityAnchor, entity_id)
    boundary = dict(DEFAULT_PHASE04_BOUNDARY)
    if row is None:
        db.add(
            CortexCanonicalIdentityAnchor(
                canonical_entity_id=entity_id,
                tenant_id=mat.tenant_id,
                bundle_id=mat.bundle_id,
                canonical_object_kind=mat.canonical_object_kind,
                provider_identity_hash=pid_hash,
                provider_identity_json=prof,
                logical_key_hash=mat.logical_key_hash,
                materialization_id=mat.id,
                raw_record_id=mat.raw_record_id,
                connector=connector,
                phase04_boundary_json=boundary,
                engine_build_ref=IDENTITY_ENGINE_BUILD_REF,
            )
        )
    else:
        row.provider_identity_json = prof
        row.logical_key_hash = mat.logical_key_hash
        row.materialization_id = mat.id
        row.raw_record_id = mat.raw_record_id
        row.connector = connector
        row.engine_build_ref = IDENTITY_ENGINE_BUILD_REF
        row.phase04_boundary_json = boundary
    return entity_id


def get_identity_anchor(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    canonical_entity_id: uuid.UUID,
) -> CortexCanonicalIdentityAnchor | None:
    row = db.get(CortexCanonicalIdentityAnchor, canonical_entity_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def list_identity_anchors(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 50,
) -> list[CortexCanonicalIdentityAnchor]:
    lim = max(1, min(limit, 200))
    return list(
        db.scalars(
            select(CortexCanonicalIdentityAnchor)
            .where(CortexCanonicalIdentityAnchor.tenant_id == tenant_id)
            .order_by(CortexCanonicalIdentityAnchor.updated_at.desc())
            .limit(lim)
        ).all()
    )


def identity_anchor_public_dict(row: CortexCanonicalIdentityAnchor) -> dict[str, Any]:
    return {
        "canonical_entity_id": row.canonical_entity_id,
        "tenant_id": row.tenant_id,
        "bundle_id": row.bundle_id,
        "canonical_object_kind": row.canonical_object_kind,
        "provider_identity_hash": row.provider_identity_hash,
        "provider_identity_json": row.provider_identity_json,
        "logical_key_hash": row.logical_key_hash,
        "materialization_id": row.materialization_id,
        "raw_record_id": row.raw_record_id,
        "connector": row.connector,
        "phase04_boundary": row.phase04_boundary_json,
        "engine_build_ref": row.engine_build_ref,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
