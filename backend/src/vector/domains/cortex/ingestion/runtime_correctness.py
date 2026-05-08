"""Phase 01 Step 16 — runtime correctness invariant suite.

Focused on current-truth ingestion correctness:
- concurrency/retry-safe uniqueness invariants
- replay/live isolation integrity
- checkpoint scope correctness
- live idempotency key correctness
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.live_idempotency import (
    derive_logical_idempotency_key,
    derive_source_identity_key,
    derive_source_revision_key,
)
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def _check(
    checks: list[dict[str, Any]],
    *,
    check_id: str,
    passed: bool,
    detail: dict[str, Any] | str | None = None,
) -> bool:
    row: dict[str, Any] = {"id": check_id, "passed": passed}
    if detail is not None:
        row["detail"] = detail
    checks.append(row)
    return passed


def verify_runtime_correctness_invariants(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    dup_live_stmt = (
        select(
            RawIngestionRecord.connection_id,
            RawIngestionRecord.connector,
            RawIngestionRecord.resource_type,
            RawIngestionRecord.source_identity_key,
            RawIngestionRecord.source_revision_key,
            func.count().label("n"),
        )
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
    )
    dup_live = list(session.execute(dup_live_stmt).all())
    _check(
        checks,
        check_id="live_connection_scoped_uniqueness",
        passed=len(dup_live) == 0,
        detail={"violations": len(dup_live)},
    )

    dup_replay_stmt = (
        select(
            RawIngestionRecord.replay_job_id,
            RawIngestionRecord.idempotency_key,
            func.count().label("n"),
        )
        .where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.replay_job_id.is_not(None),
        )
        .group_by(RawIngestionRecord.replay_job_id, RawIngestionRecord.idempotency_key)
        .having(func.count() > 1)
    )
    dup_replay = list(session.execute(dup_replay_stmt).all())
    _check(
        checks,
        check_id="replay_job_scoped_uniqueness",
        passed=len(dup_replay) == 0,
        detail={"violations": len(dup_replay)},
    )

    bad_scope_stmt = select(func.count()).select_from(ConnectorSyncState).where(
        ConnectorSyncState.tenant_id == tenant_id,
        ConnectorSyncState.scope_key != "default",
        ConnectorSyncState.scope_key.not_like("replay:%"),
    )
    bad_scope_count = int(session.scalar(bad_scope_stmt) or 0)
    _check(
        checks,
        check_id="checkpoint_scope_namespace",
        passed=bad_scope_count == 0,
        detail={"invalid_scope_count": bad_scope_count},
    )

    live_rows = list(
        session.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
            )
        ).all()
    )
    mismatch = 0
    legacy_mismatch_excluded = 0
    first_contract_match_fetched_at = None
    expected_by_row: list[tuple[RawIngestionRecord, str]] = []
    for row in live_rows:
        expected_identity = derive_source_identity_key(
            connector=row.connector,
            resource_type=row.resource_type,
            external_id=row.external_id,
        )
        expected_revision = derive_source_revision_key(dict(row.payload_body))
        expected_key = derive_logical_idempotency_key(
            source_identity_key=expected_identity,
            source_revision_key=expected_revision,
        )[:128]
        expected_by_row.append((row, expected_key))
        if row.idempotency_key == expected_key:
            if first_contract_match_fetched_at is None or row.fetched_at < first_contract_match_fetched_at:
                first_contract_match_fetched_at = row.fetched_at

    for row, expected_key in expected_by_row:
        if row.idempotency_key == expected_key:
            continue
        if (
            first_contract_match_fetched_at is not None
            and row.fetched_at < first_contract_match_fetched_at
        ):
            legacy_mismatch_excluded += 1
            continue
        mismatch += 1
    _check(
        checks,
        check_id="live_logical_idempotency_key_matches_payload",
        passed=mismatch == 0,
        detail={
            "live_rows_examined": len(live_rows),
            "mismatches": mismatch,
            "legacy_mismatch_excluded": legacy_mismatch_excluded,
            "first_contract_match_fetched_at": (
                first_contract_match_fetched_at.isoformat()
                if first_contract_match_fetched_at is not None
                else None
            ),
        },
    )

    passed = all(c["passed"] for c in checks)
    return {"passed": passed, "checks": checks}
