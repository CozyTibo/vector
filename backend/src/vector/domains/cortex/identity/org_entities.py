"""Phase 04 Step 3 — org entity (org handle) registry runtime.

Normative: `DOCS/cortex/04-identity/phase-04-org-entity-and-handle-doctrine.md`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from enum import StrEnum
from typing import Any, Final

from sqlalchemy import nullslast, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity

ORG_ENTITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1
ORG_ENTITY_ENGINE_BUILD_REF: Final[str] = "phase04-step3-org-entities-v1"

PHASE04_ORG_ENTITY_NAMESPACE: Final[uuid.UUID] = uuid.uuid5(
    uuid.NAMESPACE_DNS,
    "vector.phase04.org_entity.v1",
)


class OrgEntityKind(StrEnum):
    """Closed v1 org entity kinds (extend via doctrine + migration)."""

    HUMAN_ACTOR = "human_actor"
    SERVICE_ACCOUNT = "service_account"
    TEAM = "team"
    WORKSPACE = "workspace"
    REPOSITORY_ASSET = "repository_asset"
    COORDINATION_THREAD = "coordination_thread"
    INITIATIVE = "initiative"
    UNKNOWN_PLACEHOLDER = "unknown_placeholder"


def identity_key_fingerprint(identity_material: dict[str, Any]) -> str:
    """SHA-256 hex of canonical JSON identity material (sorted keys)."""
    blob = json.dumps(identity_material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(blob).hexdigest()


def deterministic_org_entity_id(
    *,
    tenant_id: uuid.UUID,
    entity_kind: str,
    fingerprint: str,
) -> uuid.UUID:
    """Stable org entity id for (**G-P04-ORG-01**)."""
    name = f"{tenant_id}:{entity_kind}:{fingerprint}"
    return uuid.uuid5(PHASE04_ORG_ENTITY_NAMESPACE, name)


def org_entity_public_dict(row: CortexOrgEntity) -> dict[str, Any]:
    return {
        "org_entity_runtime_schema_version": ORG_ENTITY_RUNTIME_SCHEMA_VERSION,
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "entity_kind": row.entity_kind,
        "lifecycle_state": row.lifecycle_state,
        "superseded_by_id": str(row.superseded_by_id) if row.superseded_by_id else None,
        "identity_key_fingerprint": row.identity_key_fingerprint,
        "metadata_json": dict(row.metadata_json or {}),
        "engine_build_ref": row.engine_build_ref,
        "tombstoned_at": row.tombstoned_at.isoformat() if row.tombstoned_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def upsert_org_entity(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    entity_kind: str,
    identity_material: dict[str, Any],
    metadata_json: dict[str, Any] | None = None,
    engine_build_ref: str | None = None,
) -> CortexOrgEntity:
    """Insert or refresh one org entity row (idempotent on fingerprint triple)."""
    fp = identity_key_fingerprint(identity_material)
    eid = deterministic_org_entity_id(tenant_id=tenant_id, entity_kind=entity_kind, fingerprint=fp)
    row = db.get(CortexOrgEntity, eid)
    meta = dict(metadata_json or {})
    ref = engine_build_ref or ORG_ENTITY_ENGINE_BUILD_REF
    if row is None:
        row = CortexOrgEntity(
            id=eid,
            tenant_id=tenant_id,
            entity_kind=entity_kind,
            lifecycle_state="active",
            identity_key_fingerprint=fp,
            metadata_json=meta,
            engine_build_ref=ref,
        )
        db.add(row)
        db.flush()
        return row
    row.metadata_json = meta
    row.engine_build_ref = ref
    db.flush()
    return row


def list_org_entities(db: Session, *, tenant_id: uuid.UUID, limit: int = 100) -> list[CortexOrgEntity]:
    lim = max(1, min(limit, 200))
    return list(
        db.scalars(
            select(CortexOrgEntity)
            .where(CortexOrgEntity.tenant_id == tenant_id)
            .order_by(nullslast(CortexOrgEntity.created_at.desc()), CortexOrgEntity.id.asc())
            .limit(lim)
        ).all()
    )


def get_org_entity(db: Session, *, tenant_id: uuid.UUID, org_entity_id: uuid.UUID) -> CortexOrgEntity | None:
    row = db.get(CortexOrgEntity, org_entity_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def verify_org_entity_determinism_static() -> dict[str, Any]:
    """G-P04-ORG-01 — deterministic id + fingerprint contract (no DB)."""
    tid = uuid.uuid5(uuid.NAMESPACE_URL, "tenant-gp04-org01")
    material = {"fixture": "gp04-org01", "n": 1}
    fp = identity_key_fingerprint(material)
    a = deterministic_org_entity_id(tenant_id=tid, entity_kind="human_actor", fingerprint=fp)
    b = deterministic_org_entity_id(tenant_id=tid, entity_kind="human_actor", fingerprint=fp)
    c = deterministic_org_entity_id(
        tenant_id=tid,
        entity_kind="human_actor",
        fingerprint=identity_key_fingerprint({**material, "n": 2}),
    )
    errors: list[str] = []
    if a != b:
        errors.append("deterministic_org_entity_id not stable for same inputs")
    if a == c:
        errors.append("expected different id for different identity material")
    passed = len(errors) == 0
    return {
        "id": "G-P04-ORG-01",
        "name": "org_entity_id_determinism",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "org_entity_runtime_schema_version": ORG_ENTITY_RUNTIME_SCHEMA_VERSION},
    }
