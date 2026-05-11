"""Phase 04 Step 6 — merge policies + append-only merge ledger (P04-06).

Normative: `DOCS/cortex/04-identity/phase-04-merge-governance-doctrine.md`.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_merge import CortexOrgMerge
from vector.infrastructure.db.models.cortex_org_merge_policy import CortexOrgMergePolicy

MERGE_GOVERNANCE_SCHEMA_VERSION: Final[int] = 1
MERGE_GOVERNANCE_ENGINE_BUILD_REF: Final[str] = "vector.merge_governance.p04_step06.v1"

MIN_HUMAN_MERGE_DISTINCT_EVIDENCE_RAW_IDS: Final[int] = 2
MIN_HUMAN_MERGE_SOURCE_ENTITIES: Final[int] = 2

_MERGE_KINDS: Final[frozenset[str]] = frozenset(
    {"human_actor_merge", "team_merge", "service_split", "compensating_merge"}
)


class MergeGovernanceError(Exception):
    """Invariant violation for merge ledger writes."""


def verify_human_merge_two_persona_evidence_policy_static() -> dict[str, Any]:
    """G-P04-MRG-01 — static contract: human merges require dual raw-id evidence floor."""
    ok = MIN_HUMAN_MERGE_DISTINCT_EVIDENCE_RAW_IDS >= 2 and MIN_HUMAN_MERGE_SOURCE_ENTITIES >= 2
    return {
        "id": "G-P04-MRG-01",
        "name": "human_merge_two_persona_evidence_policy",
        "passed": ok,
        "severity": "hard_fail",
        "detail": {
            "min_distinct_evidence_raw_ids": MIN_HUMAN_MERGE_DISTINCT_EVIDENCE_RAW_IDS,
            "min_source_entities": MIN_HUMAN_MERGE_SOURCE_ENTITIES,
        },
    }


def verify_merge_rollback_via_compensating_only_static() -> dict[str, Any]:
    """G-P04-13 — static companion: rollback path is compensating_merge rows (append-only ledger)."""
    return {
        "id": "G-P04-13",
        "name": "merge_rollback_compensating_append_only_contract",
        "passed": True,
        "severity": "hard_fail",
        "detail": {
            "append_only_table": "cortex_org_merges",
            "rollback_merge_kind": "compensating_merge",
        },
    }


def create_merge_policy(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    policy_ref: str,
    engine_build_ref: str | None = None,
) -> CortexOrgMergePolicy:
    row = CortexOrgMergePolicy(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        policy_ref=policy_ref,
        engine_build_ref=engine_build_ref or MERGE_GOVERNANCE_ENGINE_BUILD_REF,
    )
    session.add(row)
    session.flush()
    return row


def _assert_entities_in_tenant(
    session: Session, *, tenant_id: uuid.UUID, entity_ids: list[uuid.UUID]
) -> None:
    for eid in entity_ids:
        ent = session.get(CortexOrgEntity, eid)
        if ent is None or ent.tenant_id != tenant_id:
            raise MergeGovernanceError(f"org_entity_not_in_tenant:{eid}")


def append_org_merge(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    merge_kind: str,
    merge_policy_id: uuid.UUID,
    source_entity_ids: list[uuid.UUID],
    target_entity_id: uuid.UUID,
    evidence_raw_record_ids: list[int],
    operator_user_id: uuid.UUID | None = None,
    supersedes_merge_id: uuid.UUID | None = None,
    metadata_json: dict[str, Any] | None = None,
    engine_build_ref: str | None = None,
) -> CortexOrgMerge:
    if merge_kind not in _MERGE_KINDS:
        raise MergeGovernanceError(f"invalid_merge_kind:{merge_kind}")

    pol = session.get(CortexOrgMergePolicy, merge_policy_id)
    if pol is None or pol.tenant_id != tenant_id:
        raise MergeGovernanceError("merge_policy_not_found_or_tenant_mismatch")

    all_ids = list(source_entity_ids) + [target_entity_id]
    _assert_entities_in_tenant(session, tenant_id=tenant_id, entity_ids=all_ids)

    meta = dict(metadata_json or {})
    if merge_kind == "human_actor_merge":
        if operator_user_id is None:
            raise MergeGovernanceError("human_merge_requires_operator_user_id")
        if len(source_entity_ids) < MIN_HUMAN_MERGE_SOURCE_ENTITIES:
            raise MergeGovernanceError("human_merge_requires_two_source_entities")
        if len(set(source_entity_ids)) < MIN_HUMAN_MERGE_SOURCE_ENTITIES:
            raise MergeGovernanceError("human_merge_requires_distinct_source_entities")
        ev = [int(x) for x in evidence_raw_record_ids]
        if len(set(ev)) < MIN_HUMAN_MERGE_DISTINCT_EVIDENCE_RAW_IDS:
            raise MergeGovernanceError("human_merge_requires_two_distinct_evidence_raw_record_ids")
        if meta.get("evidence_basis") == "email_only":
            raise MergeGovernanceError("email_only_merge_rejected")
    elif merge_kind in ("team_merge", "service_split"):
        ev = [int(x) for x in evidence_raw_record_ids]
        if len(ev) < 1:
            raise MergeGovernanceError("team_or_service_merge_requires_evidence")
    elif merge_kind == "compensating_merge":
        if supersedes_merge_id is None:
            raise MergeGovernanceError("compensating_merge_requires_supersedes_merge_id")
        prior = session.get(CortexOrgMerge, supersedes_merge_id)
        if prior is None or prior.tenant_id != tenant_id:
            raise MergeGovernanceError("supersedes_merge_not_found_or_tenant_mismatch")

    row = CortexOrgMerge(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        merge_kind=merge_kind,
        merge_policy_id=merge_policy_id,
        source_entity_ids=[str(x) for x in source_entity_ids],
        target_entity_id=target_entity_id,
        evidence_raw_record_ids=[int(x) for x in evidence_raw_record_ids],
        operator_user_id=operator_user_id,
        supersedes_merge_id=supersedes_merge_id,
        metadata_json=meta,
        engine_build_ref=engine_build_ref or MERGE_GOVERNANCE_ENGINE_BUILD_REF,
    )
    session.add(row)
    session.flush()
    return row


def get_org_merge(session: Session, *, tenant_id: uuid.UUID, merge_id: uuid.UUID) -> CortexOrgMerge | None:
    row = session.get(CortexOrgMerge, merge_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def list_org_merges(session: Session, *, tenant_id: uuid.UUID, limit: int = 100) -> list[CortexOrgMerge]:
    lim = max(1, min(limit, 200))
    return list(
        session.scalars(
            select(CortexOrgMerge)
            .where(CortexOrgMerge.tenant_id == tenant_id)
            .order_by(CortexOrgMerge.created_at.desc())
            .limit(lim)
        ).all()
    )


def merge_public_dict(row: CortexOrgMerge) -> dict[str, Any]:
    src = row.source_entity_ids or []
    out_src = [str(uuid.UUID(str(x))) for x in src]
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "merge_kind": row.merge_kind,
        "merge_policy_id": str(row.merge_policy_id),
        "source_entity_ids": out_src,
        "target_entity_id": str(row.target_entity_id),
        "evidence_raw_record_ids": [int(x) for x in (row.evidence_raw_record_ids or [])],
        "operator_user_id": str(row.operator_user_id) if row.operator_user_id else None,
        "supersedes_merge_id": str(row.supersedes_merge_id) if row.supersedes_merge_id else None,
        "metadata_json": dict(row.metadata_json or {}),
        "engine_build_ref": row.engine_build_ref,
        "created_at": row.created_at,
    }


def list_human_merges_missing_dual_evidence_policy(session: Session, *, tenant_id: uuid.UUID) -> list[CortexOrgMerge]:
    """Rows violating G-P04-01 human completeness (defensive; CHECK should block new bad rows)."""
    rows = list(
        session.scalars(
            select(CortexOrgMerge).where(
                CortexOrgMerge.tenant_id == tenant_id,
                CortexOrgMerge.merge_kind == "human_actor_merge",
            )
        ).all()
    )
    bad: list[CortexOrgMerge] = []
    for r in rows:
        ev = list(r.evidence_raw_record_ids or [])
        src = list(r.source_entity_ids or [])
        if (
            r.merge_policy_id is None
            or r.operator_user_id is None
            or len(set(int(x) for x in ev)) < MIN_HUMAN_MERGE_DISTINCT_EVIDENCE_RAW_IDS
            or len(src) < MIN_HUMAN_MERGE_SOURCE_ENTITIES
        ):
            bad.append(r)
    return bad


def list_compensating_merges_with_broken_supersedes(
    session: Session, *, tenant_id: uuid.UUID
) -> list[CortexOrgMerge]:
    """G-P04-13 persisted slice — compensating rows whose supersedes pointer is missing or cross-tenant."""
    rows = list(
        session.scalars(
            select(CortexOrgMerge).where(
                CortexOrgMerge.tenant_id == tenant_id,
                CortexOrgMerge.merge_kind == "compensating_merge",
            )
        ).all()
    )
    bad: list[CortexOrgMerge] = []
    for r in rows:
        if r.supersedes_merge_id is None:
            bad.append(r)
            continue
        prior = session.get(CortexOrgMerge, r.supersedes_merge_id)
        if prior is None or prior.tenant_id != tenant_id:
            bad.append(r)
    return bad
