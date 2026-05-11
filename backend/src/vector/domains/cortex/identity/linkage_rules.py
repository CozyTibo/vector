"""Phase 04 Step 11 — linkage rule engine: versioned frozen manifests + integrity (P04-11).

Normative: `DOCS/cortex/04-identity/phase-04-linkage-rule-engine-doctrine.md`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_link_rule_version import CortexLinkRuleVersion
from vector.infrastructure.db.models.cortex_org_link_candidate_batch import CortexOrgLinkCandidateBatch

LINK_RULE_VERSION_SCHEMA_VERSION: Final[int] = 1
LINK_RULE_VERSION_ENGINE_BUILD_REF: Final[str] = "phase04-step11-linkage-rules-v1"


class LinkageRulesError(ValueError):
    """Invalid linkage rule version parameters."""


def compute_rules_manifest_sha256(manifest: dict[str, Any]) -> str:
    """Deterministic SHA-256 over canonical JSON (sorted keys at all levels)."""
    blob = json.dumps(manifest or {}, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def verify_link_rule_rule01_static() -> dict[str, Any]:
    """G-P04-RULE-01 — static: manifest hashing is key-order invariant + stable length."""
    errors: list[str] = []
    a = compute_rules_manifest_sha256({"x": 1, "y": {"z": 3}})
    b = compute_rules_manifest_sha256({"y": {"z": 3}, "x": 1})
    if a != b:
        errors.append("manifest_hash_must_be_top_level_key_order_invariant")
    h = compute_rules_manifest_sha256({"rule_pack_id": "p04.rule01.golden", "entries": []})
    if len(h) != 64:
        errors.append("manifest_hash_length_invalid")
    passed = len(errors) == 0
    return {
        "id": "G-P04-RULE-01",
        "name": "linkage_rule_manifest_determinism",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "sample_manifest_sha256_prefix": h[:16]},
    }


def list_link_rule_version_manifest_mismatches(db: Session, *, tenant_id: uuid.UUID, limit: int = 5_000) -> list[uuid.UUID]:
    """Persisted rows whose stored hash does not match the manifest JSON."""
    lim = max(1, min(limit, 50_000))
    rows = list(
        db.scalars(
            select(CortexLinkRuleVersion)
            .where(CortexLinkRuleVersion.tenant_id == tenant_id)
            .order_by(CortexLinkRuleVersion.created_at.desc())
            .limit(lim)
        ).all()
    )
    bad: list[uuid.UUID] = []
    for r in rows:
        if compute_rules_manifest_sha256(dict(r.rules_manifest_json or {})) != (r.manifest_sha256 or ""):
            bad.append(r.id)
    return bad


def list_candidate_batches_with_rule_version_reference_errors(
    db: Session, *, tenant_id: uuid.UUID, limit: int = 5_000
) -> list[uuid.UUID]:
    """Candidate batches that pin a rule version row but disagree on semantic_version string or FK."""
    lim = max(1, min(limit, 50_000))
    batches = list(
        db.scalars(
            select(CortexOrgLinkCandidateBatch)
            .where(
                CortexOrgLinkCandidateBatch.tenant_id == tenant_id,
                CortexOrgLinkCandidateBatch.link_rule_version_id.isnot(None),
            )
            .limit(lim)
        ).all()
    )
    bad: list[uuid.UUID] = []
    for b in batches:
        vid = b.link_rule_version_id
        if vid is None:
            continue
        ver = db.get(CortexLinkRuleVersion, vid)
        if ver is None or ver.tenant_id != tenant_id or ver.semantic_version != b.rule_version:
            bad.append(b.id)
    return bad


def get_active_link_rule_version_by_semantic(
    db: Session, *, tenant_id: uuid.UUID, semantic_version: str
) -> CortexLinkRuleVersion | None:
    sv = semantic_version.strip()
    if not sv:
        return None
    return db.scalars(
        select(CortexLinkRuleVersion).where(
            CortexLinkRuleVersion.tenant_id == tenant_id,
            CortexLinkRuleVersion.semantic_version == sv,
            CortexLinkRuleVersion.lifecycle_state == "active",
        )
    ).first()


def create_link_rule_version(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    semantic_version: str,
    rules_manifest_json: dict[str, Any],
    lifecycle_state: str = "active",
    notes: str | None = None,
    engine_build_ref: str | None = None,
) -> CortexLinkRuleVersion:
    """Register a new rule pack version; recomputes and stores manifest_sha256."""
    sv = semantic_version.strip()
    if not sv:
        msg = "semantic_version required"
        raise LinkageRulesError(msg)
    ls = lifecycle_state.strip()
    if ls not in ("active", "deprecated"):
        msg = "lifecycle_state must be active or deprecated"
        raise LinkageRulesError(msg)
    manifest = dict(rules_manifest_json or {})
    sha = compute_rules_manifest_sha256(manifest)
    if ls == "active":
        conflict = db.scalars(
            select(CortexLinkRuleVersion).where(
                CortexLinkRuleVersion.tenant_id == tenant_id,
                CortexLinkRuleVersion.semantic_version == sv,
                CortexLinkRuleVersion.lifecycle_state == "active",
            )
        ).first()
        if conflict is not None:
            msg = "active_semantic_version_already_exists_for_tenant"
            raise LinkageRulesError(msg)
    row = CortexLinkRuleVersion(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        semantic_version=sv,
        rules_manifest_json=manifest,
        manifest_sha256=sha,
        lifecycle_state=ls,
        notes=notes,
        engine_build_ref=engine_build_ref or LINK_RULE_VERSION_ENGINE_BUILD_REF,
    )
    db.add(row)
    db.flush()
    return row


def list_link_rule_versions(db: Session, *, tenant_id: uuid.UUID, limit: int = 50) -> list[CortexLinkRuleVersion]:
    lim = max(1, min(limit, 200))
    return list(
        db.scalars(
            select(CortexLinkRuleVersion)
            .where(CortexLinkRuleVersion.tenant_id == tenant_id)
            .order_by(CortexLinkRuleVersion.created_at.desc())
            .limit(lim)
        ).all()
    )


def get_link_rule_version(db: Session, *, tenant_id: uuid.UUID, rule_version_id: uuid.UUID) -> CortexLinkRuleVersion | None:
    row = db.get(CortexLinkRuleVersion, rule_version_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def link_rule_version_public_dict(row: CortexLinkRuleVersion) -> dict[str, Any]:
    return {
        "link_rule_version_schema_version": LINK_RULE_VERSION_SCHEMA_VERSION,
        "id": row.id,
        "tenant_id": row.tenant_id,
        "semantic_version": row.semantic_version,
        "rules_manifest_json": dict(row.rules_manifest_json or {}),
        "manifest_sha256": row.manifest_sha256,
        "lifecycle_state": row.lifecycle_state,
        "notes": row.notes,
        "engine_build_ref": row.engine_build_ref,
        "created_at": row.created_at,
    }
