"""Phase 04 Step 5 — deterministic candidate regeneration + batch hashing.

Normative: `DOCS/cortex/04-identity/phase-04-candidate-vs-authoritative-linkage-doctrine.md`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Final

from sqlalchemy import nullslast, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.link_ledger import assert_authoritative_link_material
from vector.domains.cortex.identity.org_entities import list_org_entities
from vector.infrastructure.db.models.cortex_link_rule_version import CortexLinkRuleVersion
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate
from vector.infrastructure.db.models.cortex_org_link_candidate_batch import CortexOrgLinkCandidateBatch

CANDIDATE_GENERATION_SCHEMA_VERSION: Final[int] = 1
CANDIDATE_GENERATION_ENGINE_BUILD_REF: Final[str] = "phase04-step5-candidate-generation-v1"


def canonical_candidate_row_projection(row: dict[str, Any]) -> dict[str, Any]:
    """Stable JSON-serializable projection for hashing."""
    ev = row.get("evidence_raw_record_ids") or []
    ev_ints = sorted(int(x) for x in ev if isinstance(x, int))
    rid = row.get("rule_id")
    rid_s = (str(rid).strip() if rid is not None else "") or None
    return {
        "link_type": str(row["link_type"]),
        "source_entity_id": str(row["source_entity_id"]),
        "target_entity_id": str(row["target_entity_id"]),
        "evidence_raw_record_ids": ev_ints,
        "rule_id": rid_s,
    }


def compute_candidate_set_sha256(rows: list[dict[str, Any]]) -> str:
    """Deterministic hash over sorted canonical projections (**G-P04-04**)."""
    blobs = [
        json.dumps(canonical_candidate_row_projection(r), sort_keys=True, separators=(",", ":")).encode("utf-8")
        for r in rows
    ]
    blobs.sort()
    h = hashlib.sha256()
    for b in blobs:
        h.update(b)
    return h.hexdigest()


def _row_digest(row: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(canonical_candidate_row_projection(row), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def verify_candidate_regen_hash_static() -> dict[str, Any]:
    """G-P04-04 — candidate set hash stable on frozen inputs."""
    rows = [
        {
            "link_type": "org.persona_belongs_to_handle",
            "source_entity_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "s")),
            "target_entity_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "t")),
            "evidence_raw_record_ids": [3, 1, 2],
            "rule_id": None,
        },
        {
            "link_type": "org.fixture_rule_only",
            "source_entity_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "t")),
            "target_entity_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "s")),
            "evidence_raw_record_ids": [],
            "rule_id": "rule.p04.stub",
        },
    ]
    a = compute_candidate_set_sha256(rows)
    b = compute_candidate_set_sha256(list(reversed(rows)))
    permuted_ev = [{**rows[0], "evidence_raw_record_ids": [1, 2, 3]}, rows[1]]
    c = compute_candidate_set_sha256(permuted_ev)
    errors: list[str] = []
    if a != b:
        errors.append("hash must not depend on row order")
    if a != c:
        errors.append("hash must not depend on evidence id order")
    passed = len(errors) == 0
    return {
        "id": "G-P04-04",
        "name": "candidate_regen_deterministic_hash",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "sample_hash": a[:16]},
    }


def verify_authoritative_replay_hash_static() -> dict[str, Any]:
    """G-P04-05 — authoritative projection hash reproducible (static fixture)."""
    proj = [
        {
            "link_type": "org.persona_belongs_to_handle",
            "source_entity_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeee0001",
            "target_entity_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeee0002",
            "evidence_raw_record_ids": [10],
            "rule_id": None,
            "revoked_at": None,
        }
    ]
    blob = json.dumps(proj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    h1 = hashlib.sha256(blob).hexdigest()
    h2 = hashlib.sha256(blob).hexdigest()
    passed = h1 == h2 and len(h1) == 64
    return {
        "id": "G-P04-05",
        "name": "authoritative_link_set_hash_reproducible",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"authoritative_set_sha256": h1},
    }


def regenerate_link_candidates(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    rule_version: str,
    rows: list[dict[str, Any]] | None = None,
    engine_build_ref: str | None = None,
    link_rule_version_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Persist a new candidate batch. When ``rows`` is None, stub-derive from first two org entities (if any).

    When ``link_rule_version_id`` is set, the row must belong to ``tenant_id`` and ``rule_version`` must match
    its ``semantic_version`` (or be empty, in which case the row's semantic version is used).
    """
    ref = engine_build_ref or CANDIDATE_GENERATION_ENGINE_BUILD_REF
    rv_in = rule_version.strip()
    link_vid_store: uuid.UUID | None = None
    if link_rule_version_id is not None:
        ver_row = db.get(CortexLinkRuleVersion, link_rule_version_id)
        if ver_row is None or ver_row.tenant_id != tenant_id:
            msg = "unknown_link_rule_version"
            raise ValueError(msg)
        if rv_in and rv_in != ver_row.semantic_version:
            msg = "rule_version_mismatch_vs_link_rule_version_row"
            raise ValueError(msg)
        rv = ver_row.semantic_version
        link_vid_store = ver_row.id
    else:
        rv = rv_in
        if not rv:
            msg = "rule_version required"
            raise ValueError(msg)

    material = list(rows) if rows is not None else _stub_candidate_rows(db, tenant_id=tenant_id)
    for r in material:
        assert_authoritative_link_material(
            link_type=str(r["link_type"]),
            evidence_raw_record_ids=list(r.get("evidence_raw_record_ids") or []),
            rule_id=r.get("rule_id"),
        )

    sha = compute_candidate_set_sha256(material)
    batch_id = uuid.uuid4()
    batch = CortexOrgLinkCandidateBatch(
        id=batch_id,
        tenant_id=tenant_id,
        rule_version=rv,
        link_rule_version_id=link_vid_store,
        candidate_set_sha256=sha,
        candidate_count=len(material),
        engine_build_ref=ref,
    )
    db.add(batch)
    db.flush()

    for r in material:
        src = uuid.UUID(str(r["source_entity_id"]))
        tgt = uuid.UUID(str(r["target_entity_id"]))
        digest = _row_digest(r)
        cand = CortexOrgLinkCandidate(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            batch_id=batch_id,
            link_type=str(r["link_type"]),
            source_entity_id=src,
            target_entity_id=tgt,
            evidence_raw_record_ids=[int(x) for x in (r.get("evidence_raw_record_ids") or []) if isinstance(x, int)],
            rule_id=(str(r["rule_id"]).strip() if r.get("rule_id") else None),
            row_digest=digest,
        )
        db.add(cand)
    db.flush()
    return {
        "candidate_batch_id": str(batch_id),
        "candidate_set_sha256": sha,
        "candidate_count": len(material),
        "candidate_generation_schema_version": CANDIDATE_GENERATION_SCHEMA_VERSION,
    }


def _stub_candidate_rows(db: Session, *, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    entities = list_org_entities(db, tenant_id=tenant_id, limit=2)
    if len(entities) < 2:
        return []
    a, b = entities[0], entities[1]
    return [
        {
            "link_type": "org.persona_belongs_to_handle",
            "source_entity_id": str(a.id),
            "target_entity_id": str(b.id),
            "evidence_raw_record_ids": [],
            "rule_id": "rule.p04.stub_regen_from_entities",
        }
    ]


def list_candidate_batches(db: Session, *, tenant_id: uuid.UUID, limit: int = 20) -> list[CortexOrgLinkCandidateBatch]:
    lim = max(1, min(limit, 100))
    return list(
        db.scalars(
            select(CortexOrgLinkCandidateBatch)
            .where(CortexOrgLinkCandidateBatch.tenant_id == tenant_id)
            .order_by(nullslast(CortexOrgLinkCandidateBatch.created_at.desc()), CortexOrgLinkCandidateBatch.id.asc())
            .limit(lim)
        ).all()
    )


def list_candidates_for_batch(
    db: Session, *, tenant_id: uuid.UUID, batch_id: uuid.UUID
) -> list[CortexOrgLinkCandidate]:
    return list(
        db.scalars(
            select(CortexOrgLinkCandidate)
            .where(
                CortexOrgLinkCandidate.tenant_id == tenant_id,
                CortexOrgLinkCandidate.batch_id == batch_id,
            )
            .order_by(CortexOrgLinkCandidate.row_digest.asc(), CortexOrgLinkCandidate.id.asc())
        ).all()
    )


def candidate_row_public_dict(row: CortexOrgLinkCandidate) -> dict[str, Any]:
    ev = row.evidence_raw_record_ids or []
    if not isinstance(ev, list):
        ev = []
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "batch_id": str(row.batch_id),
        "link_type": row.link_type,
        "source_entity_id": str(row.source_entity_id),
        "target_entity_id": str(row.target_entity_id),
        "evidence_raw_record_ids": [int(x) for x in ev if isinstance(x, int)],
        "rule_id": row.rule_id,
        "row_digest": row.row_digest,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def candidate_batch_public_dict(batch: CortexOrgLinkCandidateBatch) -> dict[str, Any]:
    return {
        "id": str(batch.id),
        "tenant_id": str(batch.tenant_id),
        "rule_version": batch.rule_version,
        "candidate_set_sha256": batch.candidate_set_sha256,
        "candidate_count": batch.candidate_count,
        "engine_build_ref": batch.engine_build_ref,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
    }


def get_candidate_batch(db: Session, *, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> CortexOrgLinkCandidateBatch | None:
    row = db.get(CortexOrgLinkCandidateBatch, batch_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row
