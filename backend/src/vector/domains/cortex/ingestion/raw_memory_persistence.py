"""Phase 02 Step 2 — persistence + provenance runtime verification."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex


def _check(
    checks: list[dict[str, Any]],
    *,
    check_id: str,
    passed: bool,
    detail: dict[str, Any] | str,
) -> None:
    checks.append({"id": check_id, "passed": passed, "detail": detail})


def verify_phase02_step2_persistence_provenance(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    raw_count = int(
        session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(RawIngestionRecord.tenant_id == tenant_id)
        )
        or 0
    )
    lineage_rows = list(
        session.scalars(
            select(RawMemoryLineageIndex).where(RawMemoryLineageIndex.tenant_id == tenant_id)
        ).all()
    )
    _check(
        checks,
        check_id="s2_lineage_index_present_when_raw_exists",
        passed=(raw_count == 0) or (len(lineage_rows) > 0),
        detail={"raw_rows": raw_count, "lineage_rows": len(lineage_rows)},
    )

    non_monotonic_windows = 0
    missing_first_raw_refs = 0
    missing_latest_raw_refs = 0
    pk_mismatches = 0
    bad_chain = 0
    bad_latest_metadata = 0
    for li in lineage_rows:
        if li.first_observed_at > li.latest_observed_at:
            non_monotonic_windows += 1
        first_raw = session.scalar(
            select(RawIngestionRecord).where(
                RawIngestionRecord.id == li.first_seen_raw_id,
                RawIngestionRecord.tenant_id == tenant_id,
            )
        )
        latest_raw = session.scalar(
            select(RawIngestionRecord).where(
                RawIngestionRecord.id == li.latest_seen_raw_id,
                RawIngestionRecord.tenant_id == tenant_id,
            )
        )
        if first_raw is None:
            missing_first_raw_refs += 1
        if latest_raw is None:
            missing_latest_raw_refs += 1
            continue

        if (
            latest_raw.connection_id != li.connection_id
            or latest_raw.connector != li.connector
            or latest_raw.resource_type != li.resource_type
            or latest_raw.source_identity_key != li.source_identity_key
        ):
            pk_mismatches += 1
        expected_chain = (
            f"{li.tenant_id}:{li.connection_id}:{li.connector}:{li.resource_type}:{li.source_identity_key}"[:512]
        )
        if li.provenance_chain_id != expected_chain:
            bad_chain += 1
        if (
            li.latest_source_revision_key != latest_raw.source_revision_key
            or li.latest_payload_hash != latest_raw.payload_hash
            or li.latest_run_id != latest_raw.run_id
            or li.latest_replay_job_id != latest_raw.replay_job_id
            or li.latest_replay_version != latest_raw.replay_version
        ):
            bad_latest_metadata += 1

    _check(
        checks,
        check_id="s2_lineage_window_monotonic",
        passed=non_monotonic_windows == 0,
        detail={"non_monotonic_windows": non_monotonic_windows, "lineage_rows": len(lineage_rows)},
    )
    _check(
        checks,
        check_id="s2_lineage_raw_references_resolve",
        passed=missing_first_raw_refs == 0 and missing_latest_raw_refs == 0,
        detail={
            "missing_first_raw_refs": missing_first_raw_refs,
            "missing_latest_raw_refs": missing_latest_raw_refs,
        },
    )
    _check(
        checks,
        check_id="s2_lineage_keys_and_chain_stable",
        passed=pk_mismatches == 0 and bad_chain == 0,
        detail={"pk_mismatches": pk_mismatches, "bad_chain": bad_chain},
    )
    _check(
        checks,
        check_id="s2_lineage_latest_metadata_matches_raw",
        passed=bad_latest_metadata == 0,
        detail={"mismatches": bad_latest_metadata},
    )

    passed = all(c["passed"] for c in checks)
    state = "unverifiable" if raw_count == 0 else ("healthy" if passed else "degraded")
    return {
        "passed": passed,
        "state": state,
        "checks": checks,
        "summary": {
            "raw_rows_examined": raw_count,
            "lineage_rows_examined": len(lineage_rows),
        },
    }
