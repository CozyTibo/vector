"""Phase 02 Step 15 — reconstruction-critical lineage/revision pointer integrity."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex


def _check(
    checks: list[dict[str, Any]],
    *,
    check_id: str,
    passed: bool,
    detail: dict[str, Any] | str,
) -> None:
    checks.append({"id": check_id, "passed": passed, "detail": detail})


def verify_phase02_step15_critical_integrity(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Cross-check revision index ↔ raw rows and lineage ↔ revision heads (trust-critical pointers)."""
    checks: list[dict[str, Any]] = []

    rev_rows = list(
        session.scalars(
            select(RawMemoryRevisionIndex).where(RawMemoryRevisionIndex.tenant_id == tenant_id)
        ).all()
    )
    lineage_rows = list(
        session.scalars(
            select(RawMemoryLineageIndex).where(RawMemoryLineageIndex.tenant_id == tenant_id)
        ).all()
    )

    raw_ids = list({r.raw_id for r in rev_rows})
    raw_map: dict[int, RawIngestionRecord] = {}
    if raw_ids:
        raw_map = {
            r.id: r
            for r in session.scalars(
                select(RawIngestionRecord).where(
                    RawIngestionRecord.tenant_id == tenant_id,
                    RawIngestionRecord.id.in_(raw_ids),
                )
            ).all()
        }

    revision_raw_mismatch = 0
    revision_missing_raw = 0
    sample_bad: list[dict[str, Any]] = []
    for rv in rev_rows:
        raw = raw_map.get(rv.raw_id)
        if raw is None:
            revision_missing_raw += 1
            if len(sample_bad) < 12:
                sample_bad.append({"kind": "missing_raw", "raw_id": rv.raw_id})
            continue
        if (
            raw.tenant_id != rv.tenant_id
            or raw.connection_id != rv.connection_id
            or raw.connector != rv.connector
            or raw.resource_type != rv.resource_type
            or raw.source_identity_key != rv.source_identity_key
            or raw.source_revision_key != rv.source_revision_key
        ):
            revision_raw_mismatch += 1
            if len(sample_bad) < 12:
                sample_bad.append({"kind": "fingerprint_mismatch", "raw_id": rv.raw_id})

    _check(
        checks,
        check_id="s15_revision_raw_rows_resolve",
        passed=revision_missing_raw == 0,
        detail={"missing": revision_missing_raw, "revision_rows": len(rev_rows), "sample": sample_bad[:5]},
    )
    _check(
        checks,
        check_id="s15_revision_raw_logical_keys_match",
        passed=revision_raw_mismatch == 0,
        detail={"mismatches": revision_raw_mismatch, "revision_rows": len(rev_rows)},
    )

    lineage_head_miss = 0
    lineage_head_mismatch = 0
    lineage_samples: list[dict[str, Any]] = []
    for li in lineage_rows:
        head = session.scalar(
            select(RawMemoryRevisionIndex).where(
                RawMemoryRevisionIndex.tenant_id == li.tenant_id,
                RawMemoryRevisionIndex.connection_id == li.connection_id,
                RawMemoryRevisionIndex.connector == li.connector,
                RawMemoryRevisionIndex.resource_type == li.resource_type,
                RawMemoryRevisionIndex.source_identity_key == li.source_identity_key,
                RawMemoryRevisionIndex.source_revision_key == li.latest_source_revision_key,
            )
        )
        if head is None:
            lineage_head_miss += 1
            if len(lineage_samples) < 12:
                lineage_samples.append(
                    {"kind": "missing_head_revision", "source_identity_key": li.source_identity_key[:48]}
                )
            continue
        if head.raw_id != li.latest_seen_raw_id:
            lineage_head_mismatch += 1
            if len(lineage_samples) < 12:
                lineage_samples.append({"kind": "head_raw_id_mismatch", "raw_id": head.raw_id})

    _check(
        checks,
        check_id="s15_lineage_latest_revision_row_present",
        passed=lineage_head_miss == 0,
        detail={"missing": lineage_head_miss, "lineage_rows": len(lineage_rows)},
    )
    _check(
        checks,
        check_id="s15_lineage_latest_matches_revision_head_raw_id",
        passed=lineage_head_mismatch == 0,
        detail={"mismatches": lineage_head_mismatch, "sample": lineage_samples[:5]},
    )

    lineage_first_miss = 0
    lineage_first_mismatch = 0
    for li in lineage_rows:
        first_raw = session.scalar(
            select(RawIngestionRecord).where(
                RawIngestionRecord.id == li.first_seen_raw_id,
                RawIngestionRecord.tenant_id == tenant_id,
            )
        )
        if first_raw is None:
            lineage_first_miss += 1
            continue
        rev_first = session.scalar(
            select(RawMemoryRevisionIndex).where(
                RawMemoryRevisionIndex.tenant_id == li.tenant_id,
                RawMemoryRevisionIndex.connection_id == li.connection_id,
                RawMemoryRevisionIndex.connector == li.connector,
                RawMemoryRevisionIndex.resource_type == li.resource_type,
                RawMemoryRevisionIndex.source_identity_key == li.source_identity_key,
                RawMemoryRevisionIndex.source_revision_key == first_raw.source_revision_key,
            )
        )
        if rev_first is None:
            lineage_first_miss += 1
            continue
        if rev_first.raw_id != li.first_seen_raw_id:
            lineage_first_mismatch += 1

    _check(
        checks,
        check_id="s15_lineage_first_revision_aligns_index",
        passed=lineage_first_miss == 0 and lineage_first_mismatch == 0,
        detail={
            "missing_first_revision_row": lineage_first_miss,
            "first_raw_id_mismatch": lineage_first_mismatch,
            "lineage_rows": len(lineage_rows),
        },
    )

    passed = all(c["passed"] for c in checks)
    return {
        "passed": passed,
        "state": "integrity_sound" if passed else "degraded",
        "checks": checks,
        "summary": {
            "revision_rows_examined": len(rev_rows),
            "lineage_rows_examined": len(lineage_rows),
            "revision_missing_raw": revision_missing_raw,
            "revision_fingerprint_mismatch": revision_raw_mismatch,
            "lineage_head_issues": lineage_head_miss + lineage_head_mismatch,
            "lineage_first_issues": lineage_first_miss + lineage_first_mismatch,
        },
    }
