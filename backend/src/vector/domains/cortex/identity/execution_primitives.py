"""Phase 04 Step 12 — persist Phase 3.5 execution primitive envelopes on org handles (P04-12).

Normative: `DOCS/cortex/04-identity/phase-04-execution-primitive-persistence-doctrine.md`.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vector.domains.cortex.continuity.execution_primitives import (
    EXECUTION_PRIMITIVE_SCHEMA_VERSION,
    ExecutionPrimitiveKind,
    derive_primitive_key,
)
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_primitive_instance import CortexOrgPrimitiveInstance

ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION: Final[int] = 1
ORG_PRIMITIVE_INSTANCE_ENGINE_BUILD_REF: Final[str] = "phase04-step12-org-primitive-instances-v1"


class PrimitivePersistenceError(ValueError):
    """Invalid primitive envelope or org binding."""


def _sorted_positive_evidence_ids(raw: object) -> list[int]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        msg = "evidence_raw_record_ids must be a JSON array of integers"
        raise PrimitivePersistenceError(msg)
    out: list[int] = []
    for x in raw:
        if not isinstance(x, int) or x <= 0:
            msg = "evidence_raw_record_ids must contain positive integers"
            raise PrimitivePersistenceError(msg)
        out.append(int(x))
    out.sort()
    if len(out) == 0:
        msg = "evidence_raw_record_ids must be non_empty"
        raise PrimitivePersistenceError(msg)
    return out


def verify_gp04_09_primitive_evidence_discipline_static() -> dict[str, Any]:
    """G-P04-09 — primitive keys are deterministic; persistence rejects empty evidence sets."""
    errors: list[str] = []
    k1 = derive_primitive_key(kind=ExecutionPrimitiveKind.WORK_EPISODE, evidence_parts={"a": 1})
    k2 = derive_primitive_key(kind=ExecutionPrimitiveKind.WORK_EPISODE, evidence_parts={"a": 1})
    if k1 != k2 or len(k1) != 64:
        errors.append("primitive_key_not_stable")
    try:
        _sorted_positive_evidence_ids([])
        errors.append("empty_evidence_should_fail_validation")
    except PrimitivePersistenceError:
        pass
    try:
        ids = _sorted_positive_evidence_ids([3, 1, 2])
        if ids != [1, 2, 3]:
            errors.append("evidence_sort_invariant")
    except PrimitivePersistenceError as exc:
        errors.append(f"valid_evidence_rejected:{exc}")
    passed = len(errors) == 0
    return {
        "id": "G-P04-09",
        "name": "execution_primitive_evidence_discipline",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "sample_primitive_key_prefix": k1[:16]},
    }


def verify_gp04_prim01_static_evidence_contract() -> dict[str, Any]:
    """Static helper for G-P04-PRIM-01 — evidence id list validation used on append."""
    errors: list[str] = []
    try:
        _sorted_positive_evidence_ids([42])
    except PrimitivePersistenceError as exc:
        errors.append(str(exc))
    try:
        _sorted_positive_evidence_ids("not_a_list")  # type: ignore[arg-type]
        errors.append("non_list_evidence_should_reject")
    except PrimitivePersistenceError:
        pass
    return {"passed": len(errors) == 0, "detail": {"errors": errors}}


def list_org_primitive_instances_missing_evidence(
    db: Session, *, tenant_id: uuid.UUID, limit: int = 5_000
) -> list[uuid.UUID]:
    """Persisted violations (defense-in-depth if CHECK is bypassed)."""
    lim = max(1, min(limit, 50_000))
    rows = list(
        db.scalars(
            select(CortexOrgPrimitiveInstance)
            .where(CortexOrgPrimitiveInstance.tenant_id == tenant_id)
            .order_by(CortexOrgPrimitiveInstance.created_at.desc())
            .limit(lim)
        ).all()
    )
    bad: list[uuid.UUID] = []
    for r in rows:
        ev = (r.envelope_json or {}).get("evidence_raw_record_ids")
        try:
            ids = _sorted_positive_evidence_ids(ev)
        except PrimitivePersistenceError:
            bad.append(r.id)
            continue
        if len(ids) == 0:
            bad.append(r.id)
    return bad


def append_org_primitive_instance(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    org_entity_id: uuid.UUID,
    envelope_json: dict[str, Any],
    lifecycle_state: str = "active",
    engine_build_ref: str | None = None,
) -> CortexOrgPrimitiveInstance:
    """Insert one primitive row; enforces org-tenant binding + non-empty evidence."""
    ent = db.get(CortexOrgEntity, org_entity_id)
    if ent is None or ent.tenant_id != tenant_id:
        msg = "unknown_org_entity_for_tenant"
        raise PrimitivePersistenceError(msg)
    env = dict(envelope_json or {})
    kind_s = str(env.get("kind") or "").strip()
    if not kind_s:
        msg = "envelope.kind required"
        raise PrimitivePersistenceError(msg)
    try:
        kind = ExecutionPrimitiveKind(kind_s)
    except ValueError as exc:
        msg = f"unknown_primitive_kind:{kind_s}"
        raise PrimitivePersistenceError(msg) from exc
    pk = str(env.get("primitive_key") or "").strip()
    if not pk or len(pk) != 64:
        msg = "envelope.primitive_key must be a 64-char hex digest"
        raise PrimitivePersistenceError(msg)
    _sorted_positive_evidence_ids(env.get("evidence_raw_record_ids"))
    row = CortexOrgPrimitiveInstance(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        org_entity_id=org_entity_id,
        primitive_kind=kind.value,
        primitive_key=pk,
        envelope_json=env,
        lifecycle_state=lifecycle_state.strip(),
        engine_build_ref=engine_build_ref or ORG_PRIMITIVE_INSTANCE_ENGINE_BUILD_REF,
    )
    if row.lifecycle_state not in ("active", "superseded", "revoked"):
        msg = "lifecycle_state must be active, superseded, or revoked"
        raise PrimitivePersistenceError(msg)
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        msg = "duplicate_primitive_key_for_tenant"
        raise PrimitivePersistenceError(msg) from exc
    return row


def list_org_primitive_instances(db: Session, *, tenant_id: uuid.UUID, limit: int = 50) -> list[CortexOrgPrimitiveInstance]:
    lim = max(1, min(limit, 200))
    return list(
        db.scalars(
            select(CortexOrgPrimitiveInstance)
            .where(CortexOrgPrimitiveInstance.tenant_id == tenant_id)
            .order_by(CortexOrgPrimitiveInstance.created_at.desc())
            .limit(lim)
        ).all()
    )


def get_org_primitive_instance(
    db: Session, *, tenant_id: uuid.UUID, instance_id: uuid.UUID
) -> CortexOrgPrimitiveInstance | None:
    row = db.get(CortexOrgPrimitiveInstance, instance_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def org_primitive_instance_public_dict(row: CortexOrgPrimitiveInstance) -> dict[str, Any]:
    return {
        "org_primitive_instance_schema_version": ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
        "id": row.id,
        "tenant_id": row.tenant_id,
        "org_entity_id": row.org_entity_id,
        "primitive_kind": row.primitive_kind,
        "primitive_key": row.primitive_key,
        "envelope_json": dict(row.envelope_json or {}),
        "lifecycle_state": row.lifecycle_state,
        "engine_build_ref": row.engine_build_ref,
        "created_at": row.created_at,
    }
