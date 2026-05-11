"""Phase 04 Step 9 — cross-bundle equivalence declarations (P04-09).

Normative: `DOCS/cortex/04-identity/phase-04-cross-bundle-equivalence-doctrine.md`.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_bundle_equivalence_declaration import (
    CortexBundleEquivalenceDeclaration,
)
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink

BUNDLE_EQUIVALENCE_SCHEMA_VERSION: Final[int] = 1
BUNDLE_EQUIVALENCE_ENGINE_BUILD_REF: Final[str] = "phase04-step9-bundle-equivalence-v1"


class BundleEquivalenceError(ValueError):
    """Raised when a declaration would violate P04-09 invariants."""


def normalize_bundle_pair(bundle_id_a: str, bundle_id_b: str) -> tuple[str, str]:
    """Return (left, right) with left < right lexicographically; bundles must differ."""
    a = (bundle_id_a or "").strip()
    b = (bundle_id_b or "").strip()
    if not a or not b:
        msg = "bundle_equivalence_requires_non_empty_bundle_ids"
        raise BundleEquivalenceError(msg)
    if a == b:
        msg = "bundle_equivalence_requires_distinct_bundle_ids"
        raise BundleEquivalenceError(msg)
    return (a, b) if a < b else (b, a)


def cross_bundle_edge_bundles_from_link_metadata(metadata_json: dict[str, Any] | None) -> tuple[str, str] | None:
    """If link metadata declares a cross-bundle canonical edge, return normalized pair; else None."""
    if not metadata_json or not isinstance(metadata_json, dict):
        return None
    raw = metadata_json.get("cross_bundle_canonical")
    if not isinstance(raw, dict):
        return None
    sa = raw.get("source_bundle_id")
    ta = raw.get("target_bundle_id")
    if not isinstance(sa, str) or not isinstance(ta, str):
        return None
    try:
        return normalize_bundle_pair(sa, ta)
    except BundleEquivalenceError:
        return None


def bundle_equivalence_pair_static_errors() -> list[str]:
    """Static vectors for ordered-pair contract (G-P04-BNDL-01)."""
    errors: list[str] = []
    try:
        normalize_bundle_pair("", "x")
        errors.append("expected rejection on empty bundle id")
    except BundleEquivalenceError:
        pass
    try:
        normalize_bundle_pair("same", "same")
        errors.append("expected rejection on equal bundle ids")
    except BundleEquivalenceError:
        pass
    try:
        if normalize_bundle_pair("zebra", "apple") != ("apple", "zebra"):
            errors.append("lexicographic normalization mismatch")
    except BundleEquivalenceError as exc:
        errors.append(f"unexpected error on good pair: {exc}")
    return errors


def _next_replay_ordinal(db: Session, *, tenant_id: uuid.UUID) -> int:
    current = db.scalar(
        select(func.coalesce(func.max(CortexBundleEquivalenceDeclaration.replay_ordinal), 0)).where(
            CortexBundleEquivalenceDeclaration.tenant_id == tenant_id
        )
    )
    return int(current or 0) + 1


def append_bundle_equivalence_declaration(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id_a: str,
    bundle_id_b: str,
    evidence_raw_record_ids: list[int] | None = None,
    metadata_json: dict[str, Any] | None = None,
    engine_build_ref: str | None = None,
) -> CortexBundleEquivalenceDeclaration:
    left, right = normalize_bundle_pair(bundle_id_a, bundle_id_b)
    for bid in (left, right):
        if db.get(CortexMappingBundle, bid) is None:
            msg = f"unknown_bundle_id:{bid}"
            raise BundleEquivalenceError(msg)
    row = CortexBundleEquivalenceDeclaration(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        left_bundle_id=left,
        right_bundle_id=right,
        replay_ordinal=_next_replay_ordinal(db, tenant_id=tenant_id),
        evidence_raw_record_ids=[int(x) for x in (evidence_raw_record_ids or []) if isinstance(x, int)],
        metadata_json=dict(metadata_json or {}),
        engine_build_ref=engine_build_ref or BUNDLE_EQUIVALENCE_ENGINE_BUILD_REF,
    )
    db.add(row)
    db.flush()
    return row


def list_bundle_equivalence_declarations(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 200,
    include_revoked: bool = False,
) -> list[CortexBundleEquivalenceDeclaration]:
    lim = max(1, min(limit, 500))
    stmt = select(CortexBundleEquivalenceDeclaration).where(
        CortexBundleEquivalenceDeclaration.tenant_id == tenant_id
    )
    if not include_revoked:
        stmt = stmt.where(CortexBundleEquivalenceDeclaration.revoked_at.is_(None))
    stmt = stmt.order_by(
        CortexBundleEquivalenceDeclaration.replay_ordinal.desc(),
        CortexBundleEquivalenceDeclaration.created_at.desc(),
    ).limit(lim)
    return list(db.scalars(stmt).all())


def has_active_bundle_equivalence_declaration(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id_a: str,
    bundle_id_b: str,
) -> bool:
    left, right = normalize_bundle_pair(bundle_id_a, bundle_id_b)
    hit = db.scalar(
        select(CortexBundleEquivalenceDeclaration.id).where(
            CortexBundleEquivalenceDeclaration.tenant_id == tenant_id,
            CortexBundleEquivalenceDeclaration.left_bundle_id == left,
            CortexBundleEquivalenceDeclaration.right_bundle_id == right,
            CortexBundleEquivalenceDeclaration.revoked_at.is_(None),
        )
    )
    return hit is not None


def bundle_equivalence_public_dict(row: CortexBundleEquivalenceDeclaration) -> dict[str, Any]:
    ev = row.evidence_raw_record_ids
    if not isinstance(ev, list):
        ev = []
    return {
        "bundle_equivalence_schema_version": BUNDLE_EQUIVALENCE_SCHEMA_VERSION,
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "left_bundle_id": row.left_bundle_id,
        "right_bundle_id": row.right_bundle_id,
        "replay_ordinal": row.replay_ordinal,
        "evidence_raw_record_ids": [int(x) for x in ev if isinstance(x, int)],
        "metadata_json": dict(row.metadata_json or {}),
        "engine_build_ref": row.engine_build_ref,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
    }


def list_bundle_equivalence_bndl01_violations(
    db: Session, *, tenant_id: uuid.UUID
) -> list[str]:
    """Duplicate replay_ordinal for same tenant (any row) — should not happen via append path."""
    stmt = (
        select(CortexBundleEquivalenceDeclaration.replay_ordinal, func.count())
        .where(CortexBundleEquivalenceDeclaration.tenant_id == tenant_id)
        .group_by(CortexBundleEquivalenceDeclaration.replay_ordinal)
        .having(func.count() > 1)
    )
    return [f"duplicate_replay_ordinal:{row[0]}" for row in db.execute(stmt)]


def list_bundle_equivalence_gp04_14_replay_order_violations(
    db: Session, *, tenant_id: uuid.UUID
) -> list[str]:
    """Non-revoked rows must have strictly increasing replay_ordinal along time order."""
    rows = list(
        db.scalars(
            select(CortexBundleEquivalenceDeclaration)
            .where(
                CortexBundleEquivalenceDeclaration.tenant_id == tenant_id,
                CortexBundleEquivalenceDeclaration.revoked_at.is_(None),
            )
            .order_by(
                CortexBundleEquivalenceDeclaration.created_at.asc(),
                CortexBundleEquivalenceDeclaration.id.asc(),
            )
        ).all()
    )
    violations: list[str] = []
    prev: int | None = None
    for r in rows:
        if prev is not None and r.replay_ordinal <= prev:
            violations.append(f"non_monotonic_replay_ordinal:{r.id}:{r.replay_ordinal}")
        prev = r.replay_ordinal
    return violations


def list_org_links_missing_cross_bundle_equivalence(
    db: Session, *, tenant_id: uuid.UUID, limit: int = 50_000
) -> list[CortexOrgLink]:
    """G-P04-03 — authoritative links with cross_bundle_canonical and no active declaration."""
    lim = max(1, min(limit, 50_000))
    rows = list(
        db.scalars(
            select(CortexOrgLink).where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_authority == "authoritative",
                CortexOrgLink.revoked_at.is_(None),
            ).limit(lim)
        ).all()
    )
    missing: list[CortexOrgLink] = []
    for link in rows:
        pair = cross_bundle_edge_bundles_from_link_metadata(dict(link.metadata_json or {}))
        if pair is None:
            continue
        left, right = pair
        if not has_active_bundle_equivalence_declaration(db, tenant_id=tenant_id, bundle_id_a=left, bundle_id_b=right):
            missing.append(link)
    return missing
