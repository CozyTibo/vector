"""Phase 02 Step 3 — temporal continuity runtime model and checks."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.temporal_ordering import derive_deletion_observed
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex


def _effective_ts_expr() -> Any:
    return case(
        (
            RawMemoryRevisionIndex.provider_event_timestamp.is_not(None),
            RawMemoryRevisionIndex.provider_event_timestamp,
        ),
        else_=RawMemoryRevisionIndex.fetched_at,
    )


def list_revision_chain(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    resource_type: str,
    source_identity_key: str,
) -> list[RawMemoryRevisionIndex]:
    eff = _effective_ts_expr()
    stmt = (
        select(RawMemoryRevisionIndex)
        .where(
            RawMemoryRevisionIndex.tenant_id == tenant_id,
            RawMemoryRevisionIndex.connection_id == connection_id,
            RawMemoryRevisionIndex.connector == connector,
            RawMemoryRevisionIndex.resource_type == resource_type,
            RawMemoryRevisionIndex.source_identity_key == source_identity_key,
        )
        .order_by(
            eff.asc(),
            RawMemoryRevisionIndex.source_revision_key.asc(),
            RawMemoryRevisionIndex.fetched_at.asc(),
            RawMemoryRevisionIndex.raw_id.asc(),
        )
    )
    return list(session.scalars(stmt).all())


def latest_known_before_t(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
    resource_type: str,
    source_identity_key: str,
    as_of: datetime,
) -> RawMemoryRevisionIndex | None:
    eff = _effective_ts_expr()
    stmt = (
        select(RawMemoryRevisionIndex)
        .where(
            RawMemoryRevisionIndex.tenant_id == tenant_id,
            RawMemoryRevisionIndex.connection_id == connection_id,
            RawMemoryRevisionIndex.connector == connector,
            RawMemoryRevisionIndex.resource_type == resource_type,
            RawMemoryRevisionIndex.source_identity_key == source_identity_key,
            eff <= as_of,
        )
        .order_by(
            eff.desc(),
            RawMemoryRevisionIndex.source_revision_key.desc(),
            RawMemoryRevisionIndex.fetched_at.desc(),
            RawMemoryRevisionIndex.raw_id.desc(),
        )
        .limit(1)
    )
    return session.scalar(stmt)


def _check(
    checks: list[dict[str, Any]],
    *,
    check_id: str,
    passed: bool,
    detail: dict[str, Any] | str,
) -> None:
    checks.append({"id": check_id, "passed": passed, "detail": detail})


def verify_phase02_step3_temporal_continuity(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    raw_count = int(
        session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(RawIngestionRecord.tenant_id == tenant_id)
        )
        or 0
    )
    try:
        rev_rows = list(
            session.scalars(
                select(RawMemoryRevisionIndex).where(RawMemoryRevisionIndex.tenant_id == tenant_id)
            ).all()
        )
    except ProgrammingError:
        rev_rows = []
        _check(
            checks,
            check_id="s3_temporal_index_table_present",
            passed=False,
            detail="raw_memory_revision_index table missing; apply migrations",
        )
        return {
            "passed": False,
            "state": "unverifiable",
            "checks": checks,
            "summary": {"raw_rows_examined": raw_count, "revision_rows_examined": 0},
        }

    _check(
        checks,
        check_id="s3_revision_index_present_when_raw_exists",
        passed=(raw_count == 0) or (len(rev_rows) > 0),
        detail={"raw_rows": raw_count, "revision_rows": len(rev_rows)},
    )

    missing_fetched = sum(1 for r in rev_rows if r.fetched_at is None)
    _check(
        checks,
        check_id="s3_revision_rows_have_fetched_at",
        passed=missing_fetched == 0,
        detail={"missing_fetched_at": missing_fetched, "rows_examined": len(rev_rows)},
    )

    by_identity: dict[tuple[uuid.UUID, uuid.UUID, str, str, str], list[RawMemoryRevisionIndex]] = defaultdict(list)
    for row in rev_rows:
        by_identity[
            (
                row.tenant_id,
                row.connection_id,
                row.connector,
                row.resource_type,
                row.source_identity_key,
            )
        ].append(row)
    supersession_breaks = 0
    for ident, rows in by_identity.items():
        chain = list_revision_chain(
            session,
            tenant_id=ident[0],
            connection_id=ident[1],
            connector=ident[2],
            resource_type=ident[3],
            source_identity_key=ident[4],
        )
        prev: str | None = None
        for entry in chain:
            if entry.supersedes_source_revision_key != prev:
                supersession_breaks += 1
            prev = entry.source_revision_key
    _check(
        checks,
        check_id="s3_supersession_chain_coherent",
        passed=supersession_breaks == 0,
        detail={"identities_examined": len(by_identity), "breaks": supersession_breaks},
    )

    raw_rows = list(
        session.scalars(select(RawIngestionRecord).where(RawIngestionRecord.tenant_id == tenant_id)).all()
    )
    deletion_marker_rows = 0
    deletion_visibility_mismatch = 0
    by_raw_id = {r.raw_id: r for r in rev_rows}
    for raw in raw_rows:
        body = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
        if derive_deletion_observed(body):
            deletion_marker_rows += 1
            rev = by_raw_id.get(raw.id)
            if rev is None or rev.is_deleted_observed is not True:
                deletion_visibility_mismatch += 1
    _check(
        checks,
        check_id="s3_deletion_visibility_preserved",
        passed=deletion_visibility_mismatch == 0,
        detail={
            "deletion_marker_rows": deletion_marker_rows,
            "visibility_mismatches": deletion_visibility_mismatch,
        },
    )

    nondeterministic_identities = 0
    sampled = list(by_identity.keys())[:25]
    for ident in sampled:
        first = [
            r.source_revision_key
            for r in list_revision_chain(
                session,
                tenant_id=ident[0],
                connection_id=ident[1],
                connector=ident[2],
                resource_type=ident[3],
                source_identity_key=ident[4],
            )
        ]
        second = [
            r.source_revision_key
            for r in list_revision_chain(
                session,
                tenant_id=ident[0],
                connection_id=ident[1],
                connector=ident[2],
                resource_type=ident[3],
                source_identity_key=ident[4],
            )
        ]
        if first != second:
            nondeterministic_identities += 1
    _check(
        checks,
        check_id="s3_temporal_ordering_deterministic",
        passed=nondeterministic_identities == 0,
        detail={"identities_sampled": len(sampled), "nondeterministic": nondeterministic_identities},
    )

    passed = all(c["passed"] for c in checks)
    state = "unverifiable" if raw_count == 0 else ("reconstruction-safe" if passed else "degraded")
    return {
        "passed": passed,
        "state": state,
        "checks": checks,
        "summary": {
            "raw_rows_examined": raw_count,
            "revision_rows_examined": len(rev_rows),
            "identities_examined": len(by_identity),
        },
    }
