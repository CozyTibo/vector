"""Phase 02 Step 4 — replay equivalence + divergence handling."""

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
from vector.infrastructure.db.models.raw_memory_failure_case import RawMemoryFailureCase

REPLAY_DIVERGENCE_CLASS_META: dict[str, dict[str, str]] = {
    "D0": {
        "name": "expected_equivalent",
        "severity": "S0",
        "closure_impact": "none",
    },
    "D1": {
        "name": "expected_provider_mutation",
        "severity": "S1",
        "closure_impact": "warn_only_or_soft_fail",
    },
    "D2": {
        "name": "expected_schema_reinterpretation",
        "severity": "S1",
        "closure_impact": "soft_fail_until_accepted",
    },
    "D3": {
        "name": "forbidden_scope_or_order",
        "severity": "S2",
        "closure_impact": "hard_fail",
    },
    "D4": {
        "name": "lineage_breaking_divergence",
        "severity": "S2",
        "closure_impact": "hard_fail",
    },
    "D5": {
        "name": "reconstruction_breaking_divergence",
        "severity": "S3",
        "closure_impact": "hard_fail",
    },
}
REPLAY_DIVERGENCE_CLASS_IDS: tuple[str, ...] = tuple(REPLAY_DIVERGENCE_CLASS_META.keys())
FORBIDDEN_DIVERGENCE_CLASSES: frozenset[str] = frozenset({"D3", "D4", "D5"})
_ORDER = {"D0": 0, "D1": 1, "D2": 2, "D3": 3, "D4": 4, "D5": 5}


def _class_info(cls: str) -> dict[str, str]:
    return {"class": cls, **REPLAY_DIVERGENCE_CLASS_META[cls]}


def _is_schema_reinterpretation(replay_row: RawIngestionRecord, live_row: RawIngestionRecord) -> bool:
    rb = replay_row.payload_body if isinstance(replay_row.payload_body, dict) else {}
    lb = live_row.payload_body if isinstance(live_row.payload_body, dict) else {}
    rv = rb.get("ingestion_version")
    lv = lb.get("ingestion_version")
    return isinstance(rv, dict) and isinstance(lv, dict) and rv != lv


def _classify_job(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    replay_job_id: uuid.UUID,
) -> dict[str, Any]:
    live_rows = list(
        session.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
            )
        ).all()
    )
    first_contract_match_fetched_at = None
    for live in live_rows:
        body = dict(live.payload_body) if isinstance(live.payload_body, dict) else {}
        ph_ok = canonical_payload_hash(body) == live.payload_hash
        expected_idem = derive_logical_idempotency_key(
            source_identity_key=derive_source_identity_key(
                connector=live.connector,
                resource_type=live.resource_type,
                external_id=live.external_id,
            ),
            source_revision_key=derive_source_revision_key(body),
        )[:128]
        if ph_ok and live.idempotency_key == expected_idem:
            if first_contract_match_fetched_at is None or live.fetched_at < first_contract_match_fetched_at:
                first_contract_match_fetched_at = live.fetched_at

    rows = list(
        session.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id == replay_job_id,
            )
        ).all()
    )
    if not rows:
        return {
            "replay_job_id": str(replay_job_id),
            "rows_examined": 0,
            "highest_divergence": _class_info("D0"),
            "class_counts": {"D0": 0, "D1": 0, "D2": 0, "D3": 0, "D4": 0, "D5": 0},
            "blocking": False,
            "details": [],
        }

    class_counts = {"D0": 0, "D1": 0, "D2": 0, "D3": 0, "D4": 0, "D5": 0}
    details: list[dict[str, Any]] = []
    highest = "D0"

    replay_key_counts: dict[tuple[uuid.UUID, str, str, str, str], int] = {}
    for conn_id, connector, resource_type, identity, revision, n in session.execute(
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
            RawIngestionRecord.replay_job_id == replay_job_id,
        )
        .group_by(
            RawIngestionRecord.connection_id,
            RawIngestionRecord.connector,
            RawIngestionRecord.resource_type,
            RawIngestionRecord.source_identity_key,
            RawIngestionRecord.source_revision_key,
        )
    ).all():
        replay_key_counts[(conn_id, connector, resource_type, identity, revision)] = int(n)
    duplicate_groups = sum(1 for n in replay_key_counts.values() if n > 1)
    if duplicate_groups > 0:
        class_counts["D3"] += duplicate_groups
        highest = "D3"
        details.append({"type": "duplicate_replay_logical_keys", "groups": duplicate_groups})

    first_scan = [
        int(x)
        for x in session.scalars(
            select(RawIngestionRecord.id)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id == replay_job_id,
            )
            .order_by(RawIngestionRecord.replay_sequence.asc(), RawIngestionRecord.id.asc())
        ).all()
    ]
    second_scan = [
        int(x)
        for x in session.scalars(
            select(RawIngestionRecord.id)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id == replay_job_id,
            )
            .order_by(RawIngestionRecord.replay_sequence.asc(), RawIngestionRecord.id.asc())
        ).all()
    ]
    if first_scan != second_scan:
        class_counts["D3"] += 1
        highest = "D3"
        details.append({"type": "nondeterministic_replay_order_detected"})

    cont_break_n = int(
        session.scalar(
            select(func.count())
            .select_from(RawMemoryFailureCase)
            .where(
                RawMemoryFailureCase.tenant_id == tenant_id,
                RawMemoryFailureCase.active.is_(True),
                RawMemoryFailureCase.trust_state_impact == "continuity-broken",
            )
        )
        or 0
    )
    upgrade_d4_to_d5 = cont_break_n > 0

    for row in rows:
        live_stmt = (
            select(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
                RawIngestionRecord.connection_id == row.connection_id,
                RawIngestionRecord.connector == row.connector,
                RawIngestionRecord.resource_type == row.resource_type,
                RawIngestionRecord.source_identity_key == row.source_identity_key,
                RawIngestionRecord.source_revision_key == row.source_revision_key,
            )
            .order_by(RawIngestionRecord.fetched_at.desc(), RawIngestionRecord.id.desc())
            .limit(1)
        )
        live_row = session.scalar(live_stmt)
        if live_row is None:
            # Retry on logical identity only. If identity exists but revision advanced, treat as provider mutation.
            live_identity_row = session.scalar(
                select(RawIngestionRecord)
                .where(
                    RawIngestionRecord.tenant_id == tenant_id,
                    RawIngestionRecord.replay_job_id.is_(None),
                    RawIngestionRecord.connection_id == row.connection_id,
                    RawIngestionRecord.connector == row.connector,
                    RawIngestionRecord.resource_type == row.resource_type,
                    RawIngestionRecord.source_identity_key == row.source_identity_key,
                )
                .order_by(RawIngestionRecord.fetched_at.desc(), RawIngestionRecord.id.desc())
                .limit(1)
            )
            if live_identity_row is not None:
                cls = "D2" if _is_schema_reinterpretation(row, live_identity_row) else "D1"
            # Legacy replay rows before contract cutover do not have strict live equivalence guarantees.
            elif first_contract_match_fetched_at is not None and row.fetched_at < first_contract_match_fetched_at:
                cls = "D2"
            else:
                cls = "D4"
        elif live_row.payload_hash == row.payload_hash:
            cls = "D0"
        elif _is_schema_reinterpretation(row, live_row):
            cls = "D2"
        else:
            cls = "D1"
        if cls == "D4" and upgrade_d4_to_d5:
            cls = "D5"
        class_counts[cls] += 1
        if _ORDER[cls] > _ORDER[highest]:
            highest = cls

    blocking = _ORDER[highest] >= _ORDER["D3"]
    return {
        "replay_job_id": str(replay_job_id),
        "rows_examined": len(rows),
        "highest_divergence": _class_info(highest),
        "class_counts": class_counts,
        "blocking": blocking,
        "details": details[:20],
    }


def verify_phase02_step4_replay_equivalence(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    replay_job_ids = [
        x
        for x in session.scalars(
            select(RawIngestionRecord.replay_job_id)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_not(None),
            )
            .group_by(RawIngestionRecord.replay_job_id)
        ).all()
        if x is not None
    ]
    if not replay_job_ids:
        return {
            "passed": True,
            "state": "unverifiable",
            "checks": [
                {
                    "id": "s4_replay_jobs_present",
                    "passed": True,
                    "detail": "No replay jobs observed yet; replay equivalence not exercised.",
                }
            ],
            "summary": {
                "jobs_examined": 0,
                "blocking_jobs": 0,
                "highest_divergence": _class_info("D0"),
            },
            "jobs": [],
        }

    jobs = [_classify_job(session, tenant_id=tenant_id, replay_job_id=rid) for rid in replay_job_ids]
    highest = "D0"
    blocking_jobs = 0
    for job in jobs:
        cls = str(job["highest_divergence"]["class"])
        if _ORDER[cls] > _ORDER[highest]:
            highest = cls
        if bool(job["blocking"]):
            blocking_jobs += 1
    checks = [
        {
            "id": "s4_replay_determinism_and_isolation",
            "passed": blocking_jobs == 0,
            "detail": {"blocking_jobs": blocking_jobs, "jobs_examined": len(jobs)},
        },
        {
            "id": "s4_replay_divergence_classification",
            "passed": True,
            "detail": {"highest_divergence": _class_info(highest)},
        },
    ]
    passed = blocking_jobs == 0
    state = "replay-safe" if highest == "D0" else ("partial" if _ORDER[highest] <= _ORDER["D2"] else "replay-diverged")
    return {
        "passed": passed,
        "state": state,
        "checks": checks,
        "summary": {
            "jobs_examined": len(jobs),
            "blocking_jobs": blocking_jobs,
            "highest_divergence": _class_info(highest),
        },
        "jobs": jobs,
    }
