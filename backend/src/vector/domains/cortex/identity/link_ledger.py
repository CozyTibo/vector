"""Phase 04 Step 4 — org link ledger runtime (authoritative rows).

Normative: `DOCS/cortex/04-identity/phase-04-link-ledger-doctrine.md`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import nullslast, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.boundary_checks import (
    TopologyMeaningBoundaryError,
    validate_org_link_type_not_topology,
)
from vector.domains.cortex.identity.link_classes import (
    NON_TRUTH_LINK_CLASSES,
    OrgLinkClass,
    normalize_link_class,
    row_eligible_for_merge_closure_material,
)
from vector.domains.cortex.identity.org_link_temporal import OrgLinkTemporalError, assert_org_link_validity_half_open
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink

LINK_LEDGER_RUNTIME_SCHEMA_VERSION: Final[int] = 4
LINK_LEDGER_ENGINE_BUILD_REF: Final[str] = "phase04-step8-link-ledger-v4"

MIN_VALID_TS: Final[datetime] = datetime(1970, 1, 1, tzinfo=UTC)
MAX_VALID_TS: Final[datetime] = datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC)


class LinkLedgerInvariantError(ValueError):
    """Raised when a link row would violate P04-04 invariants (evidence/rule, topology, tenant)."""


class AuthoritativeLinkDuplicatePairError(LinkLedgerInvariantError):
    """Raised when insert would violate active authoritative endpoint uniqueness (Wave S1)."""


def find_active_authoritative_org_link_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    link_type: str,
    source_entity_id: uuid.UUID,
    target_entity_id: uuid.UUID,
) -> CortexOrgLink | None:
    """Active authoritative row for this endpoint triple, if any."""
    return db.scalars(
        select(CortexOrgLink)
        .where(
            CortexOrgLink.tenant_id == tenant_id,
            CortexOrgLink.link_type == link_type,
            CortexOrgLink.source_entity_id == source_entity_id,
            CortexOrgLink.target_entity_id == target_entity_id,
            CortexOrgLink.link_authority == "authoritative",
            CortexOrgLink.revoked_at.is_(None),
        )
        .order_by(CortexOrgLink.created_at.desc(), CortexOrgLink.id.asc())
        .limit(1)
    ).first()


def material_has_evidence_or_rule(
    *,
    evidence_raw_record_ids: list[int] | None,
    rule_id: str | None,
) -> bool:
    """G-P04-LINK-01 / G-P04-06 — at least one raw evidence id or non-empty rule_id."""
    ev = evidence_raw_record_ids or []
    if len(ev) > 0:
        return True
    rid = (rule_id or "").strip()
    return bool(rid)


def assert_authoritative_link_material(
    *,
    link_type: str,
    evidence_raw_record_ids: list[int] | None,
    rule_id: str | None,
) -> None:
    if not material_has_evidence_or_rule(
        evidence_raw_record_ids=evidence_raw_record_ids,
        rule_id=rule_id,
    ):
        msg = "authoritative link requires evidence_raw_record_ids or rule_id"
        raise LinkLedgerInvariantError(msg)
    try:
        validate_org_link_type_not_topology(link_type)
    except TopologyMeaningBoundaryError as exc:
        raise LinkLedgerInvariantError(str(exc)) from exc


def link_public_dict(row: CortexOrgLink) -> dict[str, Any]:
    ev = row.evidence_raw_record_ids
    if not isinstance(ev, list):
        ev = []
    return {
        "link_ledger_runtime_schema_version": LINK_LEDGER_RUNTIME_SCHEMA_VERSION,
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "link_type": row.link_type,
        "source_entity_id": str(row.source_entity_id),
        "target_entity_id": str(row.target_entity_id),
        "evidence_raw_record_ids": [int(x) for x in ev if isinstance(x, int)],
        "rule_id": row.rule_id,
        "confidence_class": row.confidence_class,
        "valid_from": row.valid_from.isoformat() if row.valid_from else None,
        "valid_to": row.valid_to.isoformat() if row.valid_to else None,
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
        "supersedes_link_id": str(row.supersedes_link_id) if row.supersedes_link_id else None,
        "promoted_from_candidate_id": str(row.promoted_from_candidate_id)
        if row.promoted_from_candidate_id
        else None,
        "promotion_policy_id": str(row.promotion_policy_id) if row.promotion_policy_id else None,
        "link_authority": row.link_authority,
        "link_class": row.link_class,
        "metadata_json": dict(row.metadata_json or {}),
        "engine_build_ref": row.engine_build_ref,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def append_authoritative_org_link(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    link_type: str,
    source_entity_id: uuid.UUID,
    target_entity_id: uuid.UUID,
    evidence_raw_record_ids: list[int] | None = None,
    rule_id: str | None = None,
    confidence_class: str = "phase03_confidence_stub",
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    supersedes_link_id: uuid.UUID | None = None,
    metadata_json: dict[str, Any] | None = None,
    engine_build_ref: str | None = None,
    promoted_from_candidate_id: uuid.UUID | None = None,
    promotion_policy_id: uuid.UUID | None = None,
) -> CortexOrgLink:
    """Insert one authoritative link row (runtime escape hatch / tests — not public admin write in P04-04)."""
    if (promoted_from_candidate_id is None) ^ (promotion_policy_id is None):
        msg = "promoted_from_candidate_id and promotion_policy_id must be set together"
        raise LinkLedgerInvariantError(msg)
    assert_authoritative_link_material(
        link_type=link_type,
        evidence_raw_record_ids=evidence_raw_record_ids,
        rule_id=rule_id,
    )
    src = db.get(CortexOrgEntity, source_entity_id)
    dst = db.get(CortexOrgEntity, target_entity_id)
    if src is None or src.tenant_id != tenant_id:
        msg = "source_entity_id not found for tenant"
        raise LinkLedgerInvariantError(msg)
    if dst is None or dst.tenant_id != tenant_id:
        msg = "target_entity_id not found for tenant"
        raise LinkLedgerInvariantError(msg)

    existing = find_active_authoritative_org_link_v1(
        db,
        tenant_id=tenant_id,
        link_type=link_type,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
    )
    if existing is not None:
        return existing

    try:
        assert_org_link_validity_half_open(valid_from, valid_to)
    except OrgLinkTemporalError as exc:
        raise LinkLedgerInvariantError(str(exc)) from exc

    ev_list = [int(x) for x in (evidence_raw_record_ids or [])]
    row = CortexOrgLink(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        link_type=link_type,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        evidence_raw_record_ids=ev_list,
        rule_id=(rule_id.strip() if rule_id else None),
        confidence_class=confidence_class,
        valid_from=valid_from,
        valid_to=valid_to,
        supersedes_link_id=supersedes_link_id,
        promoted_from_candidate_id=promoted_from_candidate_id,
        promotion_policy_id=promotion_policy_id,
        link_authority="authoritative",
        link_class=OrgLinkClass.AUTHORITATIVE.value,
        metadata_json=dict(metadata_json or {}),
        engine_build_ref=engine_build_ref or LINK_LEDGER_ENGINE_BUILD_REF,
    )
    db.add(row)
    db.flush()
    return row


def append_non_truth_org_link(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    link_class: str,
    link_type: str,
    source_entity_id: uuid.UUID,
    target_entity_id: uuid.UUID,
    evidence_raw_record_ids: list[int] | None = None,
    rule_id: str | None = None,
    confidence_class: str = "phase03_confidence_stub",
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    supersedes_link_id: uuid.UUID | None = None,
    metadata_json: dict[str, Any] | None = None,
    engine_build_ref: str | None = None,
) -> CortexOrgLink:
    """Insert hint / inferred / prohibited row (**P04-07**); never uses authoritative authority plane."""
    lc = normalize_link_class(link_class)
    if lc not in NON_TRUTH_LINK_CLASSES:
        msg = "append_non_truth_org_link requires link_class in {hint, inferred, prohibited}"
        raise LinkLedgerInvariantError(msg)
    assert_authoritative_link_material(
        link_type=link_type,
        evidence_raw_record_ids=evidence_raw_record_ids,
        rule_id=rule_id,
    )
    src = db.get(CortexOrgEntity, source_entity_id)
    dst = db.get(CortexOrgEntity, target_entity_id)
    if src is None or src.tenant_id != tenant_id:
        msg = "source_entity_id not found for tenant"
        raise LinkLedgerInvariantError(msg)
    if dst is None or dst.tenant_id != tenant_id:
        msg = "target_entity_id not found for tenant"
        raise LinkLedgerInvariantError(msg)

    try:
        assert_org_link_validity_half_open(valid_from, valid_to)
    except OrgLinkTemporalError as exc:
        raise LinkLedgerInvariantError(str(exc)) from exc

    ev_list = [int(x) for x in (evidence_raw_record_ids or [])]
    row = CortexOrgLink(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        link_type=link_type,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        evidence_raw_record_ids=ev_list,
        rule_id=(rule_id.strip() if rule_id else None),
        confidence_class=confidence_class,
        valid_from=valid_from,
        valid_to=valid_to,
        supersedes_link_id=supersedes_link_id,
        promoted_from_candidate_id=None,
        promotion_policy_id=None,
        link_authority="non_authoritative",
        link_class=lc,
        metadata_json=dict(metadata_json or {}),
        engine_build_ref=engine_build_ref or LINK_LEDGER_ENGINE_BUILD_REF,
    )
    db.add(row)
    db.flush()
    return row


def list_org_links(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 100,
    link_authority: str | None = None,
    link_class: str | None = None,
) -> list[CortexOrgLink]:
    lim = max(1, min(limit, 200))
    stmt = select(CortexOrgLink).where(CortexOrgLink.tenant_id == tenant_id)
    if link_authority is not None:
        stmt = stmt.where(CortexOrgLink.link_authority == link_authority)
    if link_class is not None:
        stmt = stmt.where(CortexOrgLink.link_class == link_class.strip())
    return list(
        db.scalars(
            stmt.order_by(nullslast(CortexOrgLink.created_at.desc()), CortexOrgLink.id.asc()).limit(lim)
        ).all()
    )


def get_org_link(db: Session, *, tenant_id: uuid.UUID, link_id: uuid.UUID) -> CortexOrgLink | None:
    row = db.get(CortexOrgLink, link_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def soft_revoke_org_link(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    link_id: uuid.UUID,
    engine_build_ref: str | None = None,
) -> CortexOrgLink:
    """Operator-console soft revocation (**P04-18** POST ``.../links/{id}/revoke``)."""
    row = get_org_link(db, tenant_id=tenant_id, link_id=link_id)
    if row is None:
        raise LinkLedgerInvariantError("org_link_not_found")
    if row.revoked_at is not None:
        raise LinkLedgerInvariantError("org_link_already_revoked")
    row.revoked_at = datetime.now(tz=UTC)
    if engine_build_ref:
        row.engine_build_ref = engine_build_ref
    db.flush()
    return row


def list_org_link_hint_bucket(db: Session, *, tenant_id: uuid.UUID, limit: int = 100) -> list[CortexOrgLink]:
    """Read-only bucket: hint / inferred / prohibited rows (**P04-07** admin)."""
    lim = max(1, min(limit, 200))
    classes = tuple(sorted(NON_TRUTH_LINK_CLASSES))
    return list(
        db.scalars(
            select(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_class.in_(classes),
            )
            .order_by(nullslast(CortexOrgLink.created_at.desc()), CortexOrgLink.id.asc())
            .limit(lim)
        ).all()
    )


def list_links_violating_hint_authority_invariant(
    db: Session, *, tenant_id: uuid.UUID, limit: int = 50_000
) -> list[CortexOrgLink]:
    """G-P04-HINT-01 — non-truth link_class rows must use non_authoritative link_authority."""
    lim = max(1, min(limit, 50_000))
    classes = tuple(sorted(NON_TRUTH_LINK_CLASSES))
    return list(
        db.scalars(
            select(CortexOrgLink).where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_class.in_(classes),
                CortexOrgLink.link_authority != "non_authoritative",
            )
            .limit(lim)
        ).all()
    )


def _norm_interval_start(x: datetime | None) -> datetime:
    return x if x is not None else MIN_VALID_TS


def _norm_interval_end(x: datetime | None) -> datetime:
    return x if x is not None else MAX_VALID_TS


def half_open_intervals_overlap(
    a_start: datetime | None,
    a_end: datetime | None,
    b_start: datetime | None,
    b_end: datetime | None,
) -> bool:
    """Half-open [start, end) overlap test; None = unbounded on that side."""
    sa, ea = _norm_interval_start(a_start), _norm_interval_end(a_end)
    sb, eb = _norm_interval_start(b_start), _norm_interval_end(b_end)
    return sa < eb and sb < ea


def find_authoritative_temporal_overlaps(
    rows: list[CortexOrgLink],
) -> list[dict[str, Any]]:
    """Detect overlapping validity among non-revoked authoritative links with same typed edge.

    Used by tests / future warn gates; O(n^2) per key bucket (fine for unit scale).
    """
    active = [
        r
        for r in rows
        if r.revoked_at is None
        and r.link_authority == "authoritative"
        and r.link_class == OrgLinkClass.AUTHORITATIVE.value
    ]
    buckets: dict[tuple[str, str, str, str], list[CortexOrgLink]] = {}
    for r in active:
        key = (str(r.tenant_id), r.link_type, str(r.source_entity_id), str(r.target_entity_id))
        buckets.setdefault(key, []).append(r)

    violations: list[dict[str, Any]] = []
    for key, bucket in buckets.items():
        for i in range(len(bucket)):
            for j in range(i + 1, len(bucket)):
                a, b = bucket[i], bucket[j]
                if half_open_intervals_overlap(a.valid_from, a.valid_to, b.valid_from, b.valid_to):
                    violations.append(
                        {
                            "tenant_id": key[0],
                            "link_type": key[1],
                            "source_entity_id": key[2],
                            "target_entity_id": key[3],
                            "link_id_a": str(a.id),
                            "link_id_b": str(b.id),
                        }
                    )
    return violations


def list_authoritative_temporal_overlap_violations_for_tenant(
    db: Session, *, tenant_id: uuid.UUID, limit: int = 50_000
) -> list[dict[str, Any]]:
    """G-P04-TMP-01 — persisted overlap scan (high cap; do not use list_org_links default)."""
    lim = max(1, min(limit, 50_000))
    rows = list(
        db.scalars(
            select(CortexOrgLink).where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_authority == "authoritative",
                CortexOrgLink.link_class == OrgLinkClass.AUTHORITATIVE.value,
                CortexOrgLink.revoked_at.is_(None),
            ).limit(lim)
        ).all()
    )
    return find_authoritative_temporal_overlaps(rows)


def list_org_link_temporal_timeline(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 50,
    include_revoked: bool = False,
) -> list[CortexOrgLink]:
    """Recent links ordered for temporal admin strip (valid_from desc, then created_at)."""
    lim = max(1, min(limit, 100))
    stmt = select(CortexOrgLink).where(CortexOrgLink.tenant_id == tenant_id)
    if not include_revoked:
        stmt = stmt.where(CortexOrgLink.revoked_at.is_(None))
    return list(
        db.scalars(
            stmt.order_by(nullslast(CortexOrgLink.valid_from.desc()), CortexOrgLink.created_at.desc()).limit(lim)
        ).all()
    )


def list_links_failing_evidence_or_rule(
    db: Session, *, tenant_id: uuid.UUID, limit: int = 10_000
) -> list[CortexOrgLink]:
    """Rows that violate the evidence-or-rule predicate (should be empty when DB CHECK is enforced)."""
    lim = max(1, min(limit, 50_000))
    rows = list(
        db.scalars(
            select(CortexOrgLink)
            .where(CortexOrgLink.tenant_id == tenant_id)
            .limit(lim)
        ).all()
    )
    return [r for r in rows if not material_has_evidence_or_rule_from_row(r)]


def canonical_authoritative_link_projection(row: CortexOrgLink) -> dict[str, Any]:
    ev = row.evidence_raw_record_ids or []
    if not isinstance(ev, list):
        ev = []
    ev_ints = sorted(int(x) for x in ev if isinstance(x, int))
    return {
        "id": str(row.id),
        "link_type": row.link_type,
        "source_entity_id": str(row.source_entity_id),
        "target_entity_id": str(row.target_entity_id),
        "evidence_raw_record_ids": ev_ints,
        "rule_id": (row.rule_id.strip() if row.rule_id else None),
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
    }


def compute_authoritative_link_set_sha256(db: Session, *, tenant_id: uuid.UUID) -> str:
    """Deterministic hash over all authoritative links for replay receipts (**G-P04-05**)."""
    rows = list_org_links(db, tenant_id=tenant_id, limit=50_000, link_authority="authoritative")
    rows = [r for r in rows if row_eligible_for_merge_closure_material(r)]
    blobs = [
        json.dumps(canonical_authoritative_link_projection(r), sort_keys=True, separators=(",", ":")).encode("utf-8")
        for r in rows
    ]
    blobs.sort()
    h = hashlib.sha256()
    for b in blobs:
        h.update(b)
    return h.hexdigest()


def material_has_evidence_or_rule_from_row(row: CortexOrgLink) -> bool:
    ev = row.evidence_raw_record_ids
    if isinstance(ev, list) and len(ev) > 0:
        return True
    return bool((row.rule_id or "").strip())


def verify_link_ledger_evidence_rule_static() -> dict[str, Any]:
    """G-P04-LINK-01 — static material contract (no DB)."""
    errors: list[str] = []
    try:
        assert_authoritative_link_material(
            link_type="org.persona_belongs_to_handle",
            evidence_raw_record_ids=[],
            rule_id=None,
        )
        errors.append("expected rejection when both evidence and rule empty")
    except LinkLedgerInvariantError:
        pass

    try:
        assert_authoritative_link_material(
            link_type="org.persona_belongs_to_handle",
            evidence_raw_record_ids=[1],
            rule_id=None,
        )
    except LinkLedgerInvariantError as exc:
        errors.append(f"unexpected rejection on evidence-only: {exc}")

    try:
        assert_authoritative_link_material(
            link_type="org.fixture_rule_only",
            evidence_raw_record_ids=[],
            rule_id="rule.phase04.step04.fixture.v1",
        )
    except LinkLedgerInvariantError as exc:
        errors.append(f"unexpected rejection on rule-only: {exc}")

    try:
        assert_authoritative_link_material(
            link_type="contained_in",
            evidence_raw_record_ids=[1],
            rule_id=None,
        )
        errors.append("expected topology rejection for structural link_type")
    except LinkLedgerInvariantError:
        pass

    passed = len(errors) == 0
    return {
        "id": "G-P04-LINK-01",
        "name": "org_link_evidence_or_rule_material",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "link_ledger_runtime_schema_version": LINK_LEDGER_RUNTIME_SCHEMA_VERSION},
    }
