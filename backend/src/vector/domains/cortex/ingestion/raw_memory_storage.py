"""Phase 02 Step 6 — storage + retention runtime behavior."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, select, update
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_archive_catalog import RawMemoryArchiveCatalog
from vector.infrastructure.db.models.raw_memory_retention_event import RawMemoryRetentionEvent


def apply_raw_memory_retention_policy(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    dry_run: bool = True,
    archive_after_days: int = 30,
    delete_after_days: int = 365,
    allow_delete: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    ts = now or datetime.now(tz=UTC)
    archive_cutoff = ts - timedelta(days=max(1, archive_after_days))
    delete_cutoff = ts - timedelta(days=max(1, delete_after_days))

    rows = session.execute(
        select(RawMemoryArchiveCatalog, RawIngestionRecord)
        .join(RawIngestionRecord, RawIngestionRecord.id == RawMemoryArchiveCatalog.raw_id)
        .where(RawMemoryArchiveCatalog.tenant_id == tenant_id)
    ).all()
    archive_ids: list[int] = []
    delete_ids: list[int] = []
    for cat, raw in rows:
        if raw.fetched_at <= delete_cutoff:
            delete_ids.append(raw.id)
        elif cat.storage_tier == "hot" and raw.fetched_at <= archive_cutoff:
            archive_ids.append(raw.id)

    if not dry_run:
        if archive_ids:
            for rid in archive_ids:
                session.execute(
                    update(RawMemoryArchiveCatalog)
                    .where(
                        RawMemoryArchiveCatalog.tenant_id == tenant_id,
                        RawMemoryArchiveCatalog.raw_id == rid,
                    )
                    .values(
                        storage_tier="cold",
                        archived_at=ts,
                        archive_pointer=f"db://raw_ingestion_records/{rid}",
                        metadata_json={"archived_by_policy": True},
                    )
                )
                session.add(
                    RawMemoryRetentionEvent(
                        tenant_id=tenant_id,
                        raw_id=rid,
                        event_type="archive_marked",
                        detail={"archive_after_days": archive_after_days},
                    )
                )

        if delete_ids and not allow_delete:
            for rid in delete_ids:
                session.add(
                    RawMemoryRetentionEvent(
                        tenant_id=tenant_id,
                        raw_id=rid,
                        event_type="deletion_candidate",
                        detail={"delete_after_days": delete_after_days, "delete_executed": False},
                    )
                )
        elif delete_ids and allow_delete:
            for rid in delete_ids:
                session.add(
                    RawMemoryRetentionEvent(
                        tenant_id=tenant_id,
                        raw_id=rid,
                        event_type="deleted",
                        detail={"delete_after_days": delete_after_days, "delete_executed": True},
                    )
                )
            session.execute(
                delete(RawIngestionRecord).where(
                    and_(RawIngestionRecord.tenant_id == tenant_id, RawIngestionRecord.id.in_(delete_ids))
                )
            )
        session.flush()
    return {
        "tenant_id": str(tenant_id),
        "dry_run": dry_run,
        "archive_after_days": archive_after_days,
        "delete_after_days": delete_after_days,
        "archive_candidate_count": len(archive_ids),
        "delete_candidate_count": len(delete_ids),
        "archive_candidate_ids": archive_ids[:50],
        "delete_candidate_ids": delete_ids[:50],
        "deletes_executed": bool(delete_ids and (not dry_run) and allow_delete),
    }


def verify_phase02_step6_storage_retention(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    try:
        raw_rows = list(
            session.scalars(
                select(RawIngestionRecord).where(RawIngestionRecord.tenant_id == tenant_id)
            ).all()
        )
        cat_rows = list(
            session.scalars(
                select(RawMemoryArchiveCatalog).where(RawMemoryArchiveCatalog.tenant_id == tenant_id)
            ).all()
        )
    except ProgrammingError:
        return {
            "passed": False,
            "state": "unverifiable",
            "checks": [
                {
                    "id": "s6_storage_catalog_table_present",
                    "passed": False,
                    "detail": "raw_memory_archive_catalog table missing; apply migrations",
                }
            ],
        }

    checks.append(
        {
            "id": "s6_catalog_coverage_matches_raw",
            "passed": len(raw_rows) == len(cat_rows),
            "detail": {"raw_rows": len(raw_rows), "catalog_rows": len(cat_rows)},
        }
    )
    cat_by_raw = {c.raw_id: c for c in cat_rows}
    hash_mismatch = 0
    bad_tier = 0
    cold_missing_pointer = 0
    for raw in raw_rows:
        cat = cat_by_raw.get(raw.id)
        if cat is None:
            hash_mismatch += 1
            continue
        if cat.payload_hash != raw.payload_hash:
            hash_mismatch += 1
        if cat.storage_tier not in {"hot", "cold"}:
            bad_tier += 1
        if cat.storage_tier == "cold" and (not cat.archive_pointer or cat.archived_at is None):
            cold_missing_pointer += 1
    checks.append(
        {
            "id": "s6_catalog_payload_hash_alignment",
            "passed": hash_mismatch == 0,
            "detail": {"mismatch_count": hash_mismatch},
        }
    )
    checks.append(
        {
            "id": "s6_storage_tier_validity",
            "passed": bad_tier == 0,
            "detail": {"invalid_tier_rows": bad_tier},
        }
    )
    checks.append(
        {
            "id": "s6_cold_rows_have_archive_pointer",
            "passed": cold_missing_pointer == 0,
            "detail": {"cold_rows_missing_pointer": cold_missing_pointer},
        }
    )

    dry1 = apply_raw_memory_retention_policy(session, tenant_id=tenant_id, dry_run=True)
    dry2 = apply_raw_memory_retention_policy(session, tenant_id=tenant_id, dry_run=True)
    deterministic = (
        dry1["archive_candidate_count"] == dry2["archive_candidate_count"]
        and dry1["delete_candidate_count"] == dry2["delete_candidate_count"]
    )
    checks.append(
        {
            "id": "s6_retention_policy_dry_run_deterministic",
            "passed": deterministic,
            "detail": {
                "archive_candidates": dry1["archive_candidate_count"],
                "delete_candidates": dry1["delete_candidate_count"],
            },
        }
    )

    passed = all(c["passed"] for c in checks)
    state = "unverifiable" if len(raw_rows) == 0 else ("healthy" if passed else "degraded")
    return {
        "passed": passed,
        "state": state,
        "checks": checks,
        "summary": {
            "raw_rows_examined": len(raw_rows),
            "catalog_rows_examined": len(cat_rows),
            "retention_dry_run": {
                "archive_candidate_count": dry1["archive_candidate_count"],
                "delete_candidate_count": dry1["delete_candidate_count"],
            },
        },
    }
