"""Phase 03 Step 11 — provenance records: forward raw→canonical index + derivation envelope.

Normative: `DOCS/cortex/03-canonical/phase-03-provenance-traceability-doctrine.md`.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_canonical_provenance_record import CortexCanonicalProvenanceRecord
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)

PROVENANCE_RUNTIME_SCHEMA_VERSION: Final[int] = 1


def _sorted_unique_rule_ids(specs: Sequence[Any]) -> list[str]:
    return sorted({str(getattr(sp, "rule_id", "")) for sp in specs if getattr(sp, "rule_id", None) is not None})


def upsert_provenance_for_materialization(
    db: Session,
    mat: CortexCanonicalTransformMaterialization,
    *,
    specs: Sequence[Any],
    parent_materialization_id: uuid.UUID | None = None,
    evidence_shape: str = "1:1",
) -> CortexCanonicalProvenanceRecord:
    """Persist one provenance row keyed by materialization (replaces implicitly via CASCADE on mat replace)."""
    rule_ids = _sorted_unique_rule_ids(specs)
    row = CortexCanonicalProvenanceRecord(
        materialization_id=mat.id,
        tenant_id=mat.tenant_id,
        bundle_id=mat.bundle_id,
        raw_record_id=mat.raw_record_id,
        canonical_object_kind=mat.canonical_object_kind,
        logical_key_hash=mat.logical_key_hash,
        evidence_shape=evidence_shape,
        primary_raw_record_ids=[mat.raw_record_id],
        rule_ids_involved=rule_ids,
        derivation_json={
            "stage": "canonicalize",
            "mapping_bundle_id": mat.bundle_id,
            "engine_build_ref": mat.engine_build_ref,
        },
        parent_materialization_id=parent_materialization_id,
    )
    db.add(row)
    db.flush()
    return row


def provenance_public_dict(row: CortexCanonicalProvenanceRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "materialization_id": row.materialization_id,
        "tenant_id": row.tenant_id,
        "bundle_id": row.bundle_id,
        "raw_record_id": row.raw_record_id,
        "canonical_object_kind": row.canonical_object_kind,
        "logical_key_hash": row.logical_key_hash,
        "evidence_shape": row.evidence_shape,
        "primary_raw_record_ids": list(row.primary_raw_record_ids),
        "rule_ids_involved": list(row.rule_ids_involved),
        "derivation_json": dict(row.derivation_json),
        "parent_materialization_id": row.parent_materialization_id,
        "created_at": row.created_at,
    }


def list_provenance_for_raw_record(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    raw_record_id: int,
    limit: int = 50,
) -> list[CortexCanonicalProvenanceRecord]:
    """Forward index: all canonical projections citing this raw row (tenant scoped)."""
    lim = max(1, min(limit, 200))
    return list(
        db.scalars(
            select(CortexCanonicalProvenanceRecord)
            .where(
                CortexCanonicalProvenanceRecord.tenant_id == tenant_id,
                CortexCanonicalProvenanceRecord.raw_record_id == raw_record_id,
            )
            .order_by(CortexCanonicalProvenanceRecord.created_at.desc())
            .limit(lim)
        ).all()
    )


def get_provenance_for_materialization(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    materialization_id: uuid.UUID,
) -> CortexCanonicalProvenanceRecord | None:
    return db.scalars(
        select(CortexCanonicalProvenanceRecord).where(
            CortexCanonicalProvenanceRecord.tenant_id == tenant_id,
            CortexCanonicalProvenanceRecord.materialization_id == materialization_id,
        )
    ).first()
