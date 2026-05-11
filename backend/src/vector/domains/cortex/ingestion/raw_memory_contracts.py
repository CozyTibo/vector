"""Phase 02 Step 1 — runtime contracts + invariants for raw memory."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.live_idempotency import (
    canonical_payload_hash,
    derive_logical_idempotency_key,
    derive_source_identity_key,
    derive_source_revision_key,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

def _check(
    checks: list[dict[str, Any]],
    *,
    check_id: str,
    passed: bool,
    detail: dict[str, Any] | str,
) -> None:
    checks.append({"id": check_id, "passed": passed, "detail": detail})


def _expected_logical_idem(row: RawIngestionRecord) -> str:
    body = dict(row.payload_body) if isinstance(row.payload_body, dict) else {}
    source_identity_key = derive_source_identity_key(
        connector=row.connector,
        resource_type=row.resource_type,
        external_id=row.external_id,
    )
    source_revision_key = derive_source_revision_key(body)
    return derive_logical_idempotency_key(
        source_identity_key=source_identity_key,
        source_revision_key=source_revision_key,
    )[:128]


def _has_required_provenance_fields(body: dict[str, Any]) -> bool:
    if not isinstance(body.get("schema_version"), int):
        return False
    if not str(body.get("connector_type", "")).strip():
        return False
    if not str(body.get("connector_instance_id", "")).strip():
        return False
    if not str(body.get("source_object_type", "")).strip():
        return False
    if body.get("source_object_id") in (None, ""):
        return False
    ingestion_version = body.get("ingestion_version")
    if not isinstance(ingestion_version, dict):
        return False
    for key in ("schema_version", "processor_version", "extraction_version"):
        if key not in ingestion_version:
            return False
    return True


def _phase2_state(*, checks: list[dict[str, Any]], live_rows_examined: int) -> str:
    if live_rows_examined == 0:
        return "unverifiable"
    if any(c["id"] == "i1_raw_payload_immutability" and not c["passed"] for c in checks):
        return "corrupted"
    if any(not c["passed"] for c in checks):
        return "degraded"
    return "healthy"


def verify_phase02_step1_runtime_contracts(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    live_rows = list(
        session.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
            )
        ).all()
    )
    replay_rows = list(
        session.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_not(None),
            )
        ).all()
    )

    # Establish cutover anchor so pre-step15 rows don't fail step1 hardening checks.
    first_contract_match_fetched_at = None
    for row in live_rows:
        body = dict(row.payload_body) if isinstance(row.payload_body, dict) else {}
        ph_ok = canonical_payload_hash(body) == row.payload_hash
        idem_ok = _expected_logical_idem(row) == row.idempotency_key
        if ph_ok and idem_ok:
            if first_contract_match_fetched_at is None or row.fetched_at < first_contract_match_fetched_at:
                first_contract_match_fetched_at = row.fetched_at

    # I1 Raw payload immutability
    immutable_mismatch = 0
    immutable_legacy_excluded = 0
    for row in live_rows:
        body = dict(row.payload_body) if isinstance(row.payload_body, dict) else {}
        if canonical_payload_hash(body) == row.payload_hash:
            continue
        if first_contract_match_fetched_at is not None and row.fetched_at < first_contract_match_fetched_at:
            immutable_legacy_excluded += 1
            continue
        immutable_mismatch += 1
    _check(
        checks,
        check_id="i1_raw_payload_immutability",
        passed=immutable_mismatch == 0,
        detail={
            "live_rows_examined": len(live_rows),
            "mismatches": immutable_mismatch,
            "legacy_excluded": immutable_legacy_excluded,
        },
    )

    # I2 Provenance reconstructability
    provenance_violations = 0
    for row in live_rows + replay_rows:
        body = dict(row.payload_body) if isinstance(row.payload_body, dict) else {}
        if not _has_required_provenance_fields(body):
            provenance_violations += 1
            continue
        if str(body.get("connector_type", "")).strip() != row.connector:
            provenance_violations += 1
            continue
        if str(body.get("connector_instance_id", "")).strip() != str(row.connection_id):
            provenance_violations += 1
            continue
    _check(
        checks,
        check_id="i2_provenance_reconstructability",
        passed=provenance_violations == 0,
        detail={
            "rows_examined": len(live_rows) + len(replay_rows),
            "violations": provenance_violations,
        },
    )

    # I3 Source identity + revision preservation (live lane)
    missing_identity = sum(
        1
        for row in live_rows
        if not str(row.source_identity_key or "").strip() or not str(row.source_revision_key or "").strip()
    )
    dup_live_groups = list(
        session.execute(
            select(func.count().label("n"))
            .select_from(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
            )
            .group_by(
                RawIngestionRecord.connection_id,
                RawIngestionRecord.connector,
                RawIngestionRecord.resource_type,
                RawIngestionRecord.source_identity_key,
                RawIngestionRecord.source_revision_key,
            )
            .having(func.count() > 1)
        ).all()
    )
    _check(
        checks,
        check_id="i3_source_identity_revision_preservation",
        passed=missing_identity == 0 and len(dup_live_groups) == 0,
        detail={
            "live_rows_examined": len(live_rows),
            "missing_identity_rows": missing_identity,
            "duplicate_live_groups": len(dup_live_groups),
        },
    )

    # I4 Replay lineage durability
    replay_lineage_violations = 0
    for row in replay_rows:
        body = dict(row.payload_body) if isinstance(row.payload_body, dict) else {}
        meta = body.get("cortex_replay_metadata")
        if not isinstance(meta, dict):
            replay_lineage_violations += 1
            continue
        if str(meta.get("replay_job_id", "")).strip() != str(row.replay_job_id):
            replay_lineage_violations += 1
            continue
        if row.replay_version is not None and meta.get("replay_version") != row.replay_version:
            replay_lineage_violations += 1
            continue
        if str(meta.get("sync_mode", "")).strip() != "replay":
            replay_lineage_violations += 1
            continue
    _check(
        checks,
        check_id="i4_replay_lineage_durability",
        passed=replay_lineage_violations == 0,
        detail={
            "replay_rows_examined": len(replay_rows),
            "violations": replay_lineage_violations,
        },
    )

    # I5 Deterministic retrieval for fixed scope/order.
    first_scan = [
        int(x)
        for x in session.scalars(
            select(RawIngestionRecord.id)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
            )
            .order_by(RawIngestionRecord.fetched_at.asc(), RawIngestionRecord.id.asc())
            .limit(2000)
        ).all()
    ]
    second_scan = [
        int(x)
        for x in session.scalars(
            select(RawIngestionRecord.id)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
            )
            .order_by(RawIngestionRecord.fetched_at.asc(), RawIngestionRecord.id.asc())
            .limit(2000)
        ).all()
    ]
    _check(
        checks,
        check_id="i5_deterministic_retrieval",
        passed=first_scan == second_scan,
        detail={"rows_compared": len(first_scan)},
    )

    # I6 Temporal ordering determinism anchors present.
    temporal_anchor_violations = sum(
        1
        for row in live_rows + replay_rows
        if not str(row.source_revision_key or "").strip() or row.fetched_at is None
    )
    _check(
        checks,
        check_id="i6_temporal_ordering_determinism",
        passed=temporal_anchor_violations == 0,
        detail={
            "rows_examined": len(live_rows) + len(replay_rows),
            "anchor_violations": temporal_anchor_violations,
        },
    )

    passed = all(c["passed"] for c in checks)
    state = _phase2_state(checks=checks, live_rows_examined=len(live_rows))
    return {
        "passed": passed,
        "state": state,
        "checks": checks,
        "summary": {
            "live_rows_examined": len(live_rows),
            "replay_rows_examined": len(replay_rows),
            "first_contract_match_fetched_at": (
                first_contract_match_fetched_at.isoformat()
                if first_contract_match_fetched_at is not None
                else None
            ),
        },
    }
