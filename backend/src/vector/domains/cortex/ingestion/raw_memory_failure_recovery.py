"""Phase 02 Step 7 — failure semantics + recovery validation."""

from __future__ import annotations

import hashlib
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.live_idempotency import (
    canonical_payload_hash,
    derive_logical_idempotency_key,
    derive_source_identity_key,
    derive_source_revision_key,
)
from vector.domains.cortex.ingestion.raw_memory_replay import verify_phase02_step4_replay_equivalence
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_archive_catalog import RawMemoryArchiveCatalog
from vector.infrastructure.db.models.raw_memory_failure_case import RawMemoryFailureCase
from vector.infrastructure.db.models.raw_memory_recovery_validation import RawMemoryRecoveryValidation
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex
from vector.infrastructure.db.models.tenant import Tenant

_RECOVERABILITY = {"recoverable", "conditionally_recoverable", "non_recoverable"}
_BLOCKING_TRUST_IMPACTS = {"corrupted", "continuity-broken", "replay-diverged", "unverifiable"}


def _gap_id(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def _upsert_case(session: Session, case: dict[str, Any]) -> None:
    tbl = RawMemoryFailureCase.__table__
    ins = pg_insert(tbl).values(**case)
    session.execute(
        ins.on_conflict_do_update(
            index_elements=["gap_id"],
            set_={
                "failure_class": ins.excluded.failure_class,
                "gap_type": ins.excluded.gap_type,
                "scope_connector": ins.excluded.scope_connector,
                "scope_resource_type": ins.excluded.scope_resource_type,
                "scope_source_identity_key": ins.excluded.scope_source_identity_key,
                "window_from": ins.excluded.window_from,
                "window_to": ins.excluded.window_to,
                "source": ins.excluded.source,
                "trust_state_impact": ins.excluded.trust_state_impact,
                "recoverability_class": ins.excluded.recoverability_class,
                "recovery_status": ins.excluded.recovery_status,
                "active": True,
                "detail": ins.excluded.detail,
                "updated_at": datetime.now(tz=UTC),
            },
        )
    )


def _expected_live_idempotency_key(row: RawIngestionRecord) -> str:
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


def _contract_cutover_anchor(live_rows: list[RawIngestionRecord]) -> datetime | None:
    first_contract_match_fetched_at = None
    for row in live_rows:
        body = dict(row.payload_body) if isinstance(row.payload_body, dict) else {}
        ph_ok = canonical_payload_hash(body) == row.payload_hash
        idem_ok = _expected_live_idempotency_key(row) == row.idempotency_key
        if ph_ok and idem_ok:
            if first_contract_match_fetched_at is None or row.fetched_at < first_contract_match_fetched_at:
                first_contract_match_fetched_at = row.fetched_at
    return first_contract_match_fetched_at


def sync_raw_memory_failure_cases(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    now = datetime.now(tz=UTC)
    detected: dict[str, dict[str, Any]] = {}

    # Payload mutation corruption
    rows = list(
        session.scalars(
            select(RawIngestionRecord).where(RawIngestionRecord.tenant_id == tenant_id)
        ).all()
    )
    live_rows = [row for row in rows if row.replay_job_id is None]
    first_contract_match_fetched_at = _contract_cutover_anchor(live_rows)
    for row in rows:
        body = dict(row.payload_body) if isinstance(row.payload_body, dict) else {}
        if canonical_payload_hash(body) == row.payload_hash:
            continue
        # Backward compatibility with pre-step15 rows using old hash/idempotency semantics.
        if (
            row.replay_job_id is None
            and first_contract_match_fetched_at is not None
            and row.fetched_at < first_contract_match_fetched_at
        ):
            continue
        gid = _gap_id(
            "payload_mutation_corruption",
            str(tenant_id),
            str(row.connection_id),
            row.connector,
            row.resource_type,
            row.source_identity_key,
            str(row.id),
        )
        detected[gid] = {
            "gap_id": gid,
            "tenant_id": tenant_id,
            "failure_class": "payload_mutation_corruption",
            "gap_type": "corrupted_evidence_window",
            "scope_connector": row.connector,
            "scope_resource_type": row.resource_type,
            "scope_source_identity_key": row.source_identity_key,
            "window_from": row.fetched_at,
            "window_to": row.fetched_at,
            "source": "integrity_scan",
            "trust_state_impact": "corrupted",
            "recoverability_class": "non_recoverable",
            "recovery_status": "pending",
            "last_validation_at": None,
            "active": True,
            "detail": {"raw_id": row.id, "reason": "payload_hash_mismatch"},
            "created_at": now,
            "updated_at": now,
        }

    # Lineage discontinuity from revision index supersession links
    rev_rows = list(
        session.scalars(
            select(RawMemoryRevisionIndex).where(RawMemoryRevisionIndex.tenant_id == tenant_id)
        ).all()
    )
    rev_keyset = {
        (
            r.connection_id,
            r.connector,
            r.resource_type,
            r.source_identity_key,
            r.source_revision_key,
        )
        for r in rev_rows
    }
    for row in rev_rows:
        prev = row.supersedes_source_revision_key
        if not prev:
            continue
        key = (
            row.connection_id,
            row.connector,
            row.resource_type,
            row.source_identity_key,
            prev,
        )
        if key in rev_keyset:
            continue
        gid = _gap_id(
            "lineage_discontinuity",
            str(tenant_id),
            str(row.connection_id),
            row.connector,
            row.resource_type,
            row.source_identity_key,
            row.source_revision_key,
            prev,
        )
        detected[gid] = {
            "gap_id": gid,
            "tenant_id": tenant_id,
            "failure_class": "lineage_discontinuity",
            "gap_type": "lineage_break_window",
            "scope_connector": row.connector,
            "scope_resource_type": row.resource_type,
            "scope_source_identity_key": row.source_identity_key,
            "window_from": row.fetched_at,
            "window_to": row.fetched_at,
            "source": "integrity_scan",
            "trust_state_impact": "continuity-broken",
            "recoverability_class": "recoverable",
            "recovery_status": "pending",
            "last_validation_at": None,
            "active": True,
            "detail": {
                "source_revision_key": row.source_revision_key,
                "missing_superseded_revision_key": prev,
            },
            "created_at": now,
            "updated_at": now,
        }

    # Replay divergence failures from Step 4 classifications.
    rep = verify_phase02_step4_replay_equivalence(session, tenant_id)
    for job in rep.get("jobs", []):
        highest = str(job.get("highest_divergence", {}).get("class", "D0"))
        if highest in {"D0", "D1", "D2"}:
            continue
        trust = "replay-diverged" if highest in {"D3", "D4", "D5"} else "unverifiable"
        recoverability = "recoverable" if highest in {"D3", "D4"} else "conditionally_recoverable"
        gid = _gap_id("replay_divergence", str(tenant_id), str(job["replay_job_id"]), highest)
        detected[gid] = {
            "gap_id": gid,
            "tenant_id": tenant_id,
            "failure_class": "replay_divergence",
            "gap_type": "replay_divergence_window",
            "scope_connector": None,
            "scope_resource_type": None,
            "scope_source_identity_key": None,
            "window_from": None,
            "window_to": None,
            "source": "replay",
            "trust_state_impact": trust,
            "recoverability_class": recoverability,
            "recovery_status": "pending",
            "last_validation_at": None,
            "active": True,
            "detail": job,
            "created_at": now,
            "updated_at": now,
        }

    # Partial replay completion
    failed_replays = list(
        session.scalars(
            select(IngestionRun).where(
                IngestionRun.tenant_id == tenant_id,
                IngestionRun.replay_mode.is_(True),
                IngestionRun.status == "FAILED",
                IngestionRun.replay_job_id.is_not(None),
            )
        ).all()
    )
    for run in failed_replays:
        gid = _gap_id("partial_replay_completion", str(tenant_id), str(run.replay_job_id), str(run.id))
        detected[gid] = {
            "gap_id": gid,
            "tenant_id": tenant_id,
            "failure_class": "partial_replay_completion",
            "gap_type": "replay_divergence_window",
            "scope_connector": run.connector,
            "scope_resource_type": None,
            "scope_source_identity_key": None,
            "window_from": run.started_at,
            "window_to": run.finished_at,
            "source": "replay",
            "trust_state_impact": "degraded",
            "recoverability_class": "recoverable",
            "recovery_status": "pending",
            "last_validation_at": None,
            "active": True,
            "detail": {"run_id": str(run.id), "replay_job_id": str(run.replay_job_id)},
            "created_at": now,
            "updated_at": now,
        }

    # Archival pointer corruption
    cold_rows = list(
        session.scalars(
            select(RawMemoryArchiveCatalog).where(
                RawMemoryArchiveCatalog.tenant_id == tenant_id,
                RawMemoryArchiveCatalog.storage_tier == "cold",
            )
        ).all()
    )
    for row in cold_rows:
        if row.archive_pointer and row.archived_at is not None:
            continue
        gid = _gap_id("archival_pointer_corruption", str(tenant_id), str(row.raw_id))
        detected[gid] = {
            "gap_id": gid,
            "tenant_id": tenant_id,
            "failure_class": "archival_pointer_corruption",
            "gap_type": "corrupted_evidence_window",
            "scope_connector": row.connector,
            "scope_resource_type": row.resource_type,
            "scope_source_identity_key": row.source_identity_key,
            "window_from": row.archived_at,
            "window_to": row.archived_at,
            "source": "integrity_scan",
            "trust_state_impact": "degraded",
            "recoverability_class": "recoverable",
            "recovery_status": "pending",
            "last_validation_at": None,
            "active": True,
            "detail": {"raw_id": row.raw_id},
            "created_at": now,
            "updated_at": now,
        }

    for case in detected.values():
        _upsert_case(session, case)

    existing_active = list(
        session.scalars(
            select(RawMemoryFailureCase).where(
                RawMemoryFailureCase.tenant_id == tenant_id,
                RawMemoryFailureCase.active.is_(True),
            )
        ).all()
    )
    resolved = 0
    for row in existing_active:
        if row.gap_id in detected:
            continue
        row.active = False
        row.recovery_status = "resolved"
        row.updated_at = now
        resolved += 1
    session.flush()

    counts = Counter(c["failure_class"] for c in detected.values())
    return {
        "active_failure_count": len(detected),
        "resolved_count": resolved,
        "active_failure_classes": dict(counts),
    }


def _repair_derived_indexes(session: Session, tenant_id: uuid.UUID) -> None:
    # Rebuild lineage index from raw rows
    session.execute(
        text(
            """
            WITH firsts AS (
                SELECT DISTINCT ON (tenant_id, connection_id, connector, resource_type, source_identity_key)
                    tenant_id,
                    connection_id,
                    connector,
                    resource_type,
                    source_identity_key,
                    LEFT(
                        tenant_id::text || ':' || connection_id::text || ':' || connector || ':' || resource_type
                        || ':' || source_identity_key,
                        512
                    ) AS provenance_chain_id,
                    id AS first_seen_raw_id,
                    fetched_at AS first_observed_at
                FROM raw_ingestion_records
                WHERE tenant_id = :tenant_id
                ORDER BY tenant_id, connection_id, connector, resource_type, source_identity_key, fetched_at ASC, id ASC
            ),
            lasts AS (
                SELECT DISTINCT ON (tenant_id, connection_id, connector, resource_type, source_identity_key)
                    tenant_id,
                    connection_id,
                    connector,
                    resource_type,
                    source_identity_key,
                    id AS latest_seen_raw_id,
                    fetched_at AS latest_observed_at,
                    source_revision_key AS latest_source_revision_key,
                    payload_hash AS latest_payload_hash,
                    run_id AS latest_run_id,
                    replay_job_id AS latest_replay_job_id,
                    replay_version AS latest_replay_version
                FROM raw_ingestion_records
                WHERE tenant_id = :tenant_id
                ORDER BY tenant_id, connection_id, connector, resource_type, source_identity_key, fetched_at DESC, id DESC
            )
            INSERT INTO raw_memory_lineage_index (
                tenant_id, connection_id, connector, resource_type, source_identity_key,
                provenance_chain_id, first_seen_raw_id, latest_seen_raw_id, first_observed_at, latest_observed_at,
                latest_source_revision_key, latest_payload_hash, latest_run_id, latest_replay_job_id, latest_replay_version
            )
            SELECT
                f.tenant_id, f.connection_id, f.connector, f.resource_type, f.source_identity_key,
                f.provenance_chain_id, f.first_seen_raw_id, l.latest_seen_raw_id, f.first_observed_at, l.latest_observed_at,
                l.latest_source_revision_key, l.latest_payload_hash, l.latest_run_id, l.latest_replay_job_id, l.latest_replay_version
            FROM firsts f
            JOIN lasts l USING (tenant_id, connection_id, connector, resource_type, source_identity_key)
            ON CONFLICT (tenant_id, connection_id, connector, resource_type, source_identity_key)
            DO UPDATE SET
                provenance_chain_id = EXCLUDED.provenance_chain_id,
                first_seen_raw_id = EXCLUDED.first_seen_raw_id,
                latest_seen_raw_id = EXCLUDED.latest_seen_raw_id,
                first_observed_at = EXCLUDED.first_observed_at,
                latest_observed_at = EXCLUDED.latest_observed_at,
                latest_source_revision_key = EXCLUDED.latest_source_revision_key,
                latest_payload_hash = EXCLUDED.latest_payload_hash,
                latest_run_id = EXCLUDED.latest_run_id,
                latest_replay_job_id = EXCLUDED.latest_replay_job_id,
                latest_replay_version = EXCLUDED.latest_replay_version
            """
        ),
        {"tenant_id": tenant_id},
    )

    # Rebuild archive catalog rows if missing.
    session.execute(
        text(
            """
            INSERT INTO raw_memory_archive_catalog (
                raw_id, tenant_id, connection_id, connector, resource_type, source_identity_key, source_revision_key,
                payload_hash, storage_tier, archive_pointer, archived_at, retention_class, retention_policy_version, retain_until,
                metadata_json
            )
            SELECT
                r.id, r.tenant_id, r.connection_id, r.connector, r.resource_type, r.source_identity_key, r.source_revision_key,
                r.payload_hash, 'hot', NULL, NULL, 'operational_replay', 1, NULL, '{}'::jsonb
            FROM raw_ingestion_records r
            LEFT JOIN raw_memory_archive_catalog c ON c.raw_id = r.id
            WHERE r.tenant_id = :tenant_id
              AND c.raw_id IS NULL
            """
        ),
        {"tenant_id": tenant_id},
    )

    # Ensure revision rows exist and supersession chains are recomputed.
    session.execute(
        text(
            """
            INSERT INTO raw_memory_revision_index (
                tenant_id, connection_id, connector, resource_type, source_identity_key, source_revision_key,
                raw_id, provider_event_timestamp, fetched_at, supersedes_source_revision_key, is_deleted_observed,
                run_id, replay_job_id, replay_version
            )
            SELECT
                r.tenant_id, r.connection_id, r.connector, r.resource_type, r.source_identity_key, r.source_revision_key,
                r.id, NULL, r.fetched_at, NULL, false, r.run_id, r.replay_job_id, r.replay_version
            FROM raw_ingestion_records r
            LEFT JOIN raw_memory_revision_index x
              ON x.tenant_id = r.tenant_id
             AND x.connection_id = r.connection_id
             AND x.connector = r.connector
             AND x.resource_type = r.resource_type
             AND x.source_identity_key = r.source_identity_key
             AND x.source_revision_key = r.source_revision_key
            WHERE r.tenant_id = :tenant_id
              AND x.raw_id IS NULL
            """
        ),
        {"tenant_id": tenant_id},
    )
    session.execute(
        text(
            """
            WITH ordered AS (
                SELECT
                    tenant_id,
                    connection_id,
                    connector,
                    resource_type,
                    source_identity_key,
                    source_revision_key,
                    LAG(source_revision_key) OVER (
                        PARTITION BY tenant_id, connection_id, connector, resource_type, source_identity_key
                        ORDER BY COALESCE(provider_event_timestamp, fetched_at) ASC, source_revision_key ASC, fetched_at ASC, raw_id ASC
                    ) AS prev_revision
                FROM raw_memory_revision_index
                WHERE tenant_id = :tenant_id
            )
            UPDATE raw_memory_revision_index r
            SET supersedes_source_revision_key = o.prev_revision
            FROM ordered o
            WHERE r.tenant_id = o.tenant_id
              AND r.connection_id = o.connection_id
              AND r.connector = o.connector
              AND r.resource_type = o.resource_type
              AND r.source_identity_key = o.source_identity_key
              AND r.source_revision_key = o.source_revision_key
            """
        ),
        {"tenant_id": tenant_id},
    )


def run_raw_memory_recovery_validation(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    apply_repairs: bool = True,
) -> dict[str, Any]:
    if apply_repairs:
        _repair_derived_indexes(session, tenant_id)

    sync = sync_raw_memory_failure_cases(session, tenant_id)
    active_cases = list(
        session.scalars(
            select(RawMemoryFailureCase).where(
                RawMemoryFailureCase.tenant_id == tenant_id,
                RawMemoryFailureCase.active.is_(True),
            )
        ).all()
    )
    unresolved_recoverable = sum(
        1 for c in active_cases if c.recoverability_class in {"recoverable", "conditionally_recoverable"}
    )
    status = "validated" if unresolved_recoverable == 0 else "failed"
    detail = {
        "sync": sync,
        "active_failures": len(active_cases),
        "unresolved_recoverable": unresolved_recoverable,
    }
    tenant_exists = session.scalar(select(Tenant.id).where(Tenant.id == tenant_id).limit(1))
    if tenant_exists is not None:
        row = RawMemoryRecoveryValidation(
            tenant_id=tenant_id,
            status=status,
            apply_repairs=apply_repairs,
            detail=detail,
        )
        session.add(row)
    now = datetime.now(tz=UTC)
    for case in active_cases:
        case.last_validation_at = now
        if case.recoverability_class == "non_recoverable":
            case.recovery_status = "not_recoverable"
        elif status == "validated":
            case.recovery_status = "validated"
        else:
            case.recovery_status = "failed_validation"
    session.flush()
    return {
        "status": status,
        "apply_repairs": apply_repairs,
        "active_failures": len(active_cases),
        "unresolved_recoverable": unresolved_recoverable,
        "detail": detail,
    }


def verify_phase02_step7_failure_recovery(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    sync = sync_raw_memory_failure_cases(session, tenant_id)
    active_cases = list(
        session.scalars(
            select(RawMemoryFailureCase).where(
                RawMemoryFailureCase.tenant_id == tenant_id,
                RawMemoryFailureCase.active.is_(True),
            )
        ).all()
    )
    latest_validation = session.scalar(
        select(RawMemoryRecoveryValidation)
        .where(RawMemoryRecoveryValidation.tenant_id == tenant_id)
        .order_by(RawMemoryRecoveryValidation.created_at.desc(), RawMemoryRecoveryValidation.id.desc())
        .limit(1)
    )

    required_fields_ok = True
    recoverability_ok = True
    for case in active_cases:
        if not case.failure_class or not case.gap_type or not case.source or not case.trust_state_impact:
            required_fields_ok = False
        if case.recoverability_class not in _RECOVERABILITY:
            recoverability_ok = False

    recoverable_active = [
        c for c in active_cases if c.recoverability_class in {"recoverable", "conditionally_recoverable"}
    ]
    recovery_validation_present = (not recoverable_active) or (latest_validation is not None)
    blocking_failures = sum(1 for c in active_cases if c.trust_state_impact in _BLOCKING_TRUST_IMPACTS)

    checks = [
        {
            "id": "s7_failure_representation_complete",
            "passed": required_fields_ok,
            "detail": {"active_failures": len(active_cases)},
        },
        {
            "id": "s7_recoverability_class_declared",
            "passed": recoverability_ok,
            "detail": {"active_failures": len(active_cases)},
        },
        {
            "id": "s7_recovery_validation_present_for_recoverable",
            "passed": recovery_validation_present,
            "detail": {
                "recoverable_active_failures": len(recoverable_active),
                "latest_validation_status": latest_validation.status if latest_validation else None,
            },
        },
        {
            "id": "s7_blocking_failure_classes_clear",
            "passed": blocking_failures == 0,
            "detail": {"blocking_failures": blocking_failures},
        },
    ]
    passed = all(c["passed"] for c in checks)
    by_class = Counter(c.failure_class for c in active_cases)
    if not active_cases:
        state = "healthy"
    elif any(c.trust_state_impact == "corrupted" for c in active_cases):
        state = "corrupted"
    elif any(c.trust_state_impact == "continuity-broken" for c in active_cases):
        state = "continuity-broken"
    elif any(c.trust_state_impact == "replay-diverged" for c in active_cases):
        state = "replay-diverged"
    else:
        state = "degraded"
    return {
        "passed": passed,
        "state": state,
        "checks": checks,
        "summary": {
            "active_failure_count": len(active_cases),
            "active_failure_classes": dict(by_class),
            "latest_recovery_validation": (
                {
                    "status": latest_validation.status,
                    "created_at": latest_validation.created_at.isoformat(),
                }
                if latest_validation is not None
                else None
            ),
            "sync": sync,
        },
    }
