"""Phase 03 Step 14 — canonical failure registry + policy-gated remediation validation."""

from __future__ import annotations

import hashlib
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_canonical_failure_case import CortexCanonicalFailureCase
from vector.infrastructure.db.models.cortex_canonical_remediation_validation import (
    CortexCanonicalRemediationValidation,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_trust_state import RawMemoryTrustState

FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1
BLOCKING_TRUST_STATES: Final[frozenset[str]] = frozenset(
    {"corrupted", "continuity-broken", "replay-diverged"}
)
FORBIDDEN_REPLAY_DIVERGENCE: Final[frozenset[str]] = frozenset({"C3", "C4", "C5"})


def _gap_id(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def _tenant_trust_state(db: Session, *, tenant_id: uuid.UUID) -> str | None:
    row = db.get(RawMemoryTrustState, tenant_id)
    return str(row.trust_state) if row is not None else None


def _upsert_failure_case(session: Session, case: dict[str, Any]) -> None:
    tbl = CortexCanonicalFailureCase.__table__
    ins = pg_insert(tbl).values(**case)
    session.execute(
        ins.on_conflict_do_update(
            index_elements=["gap_id"],
            set_={
                "failure_class": ins.excluded.failure_class,
                "degradation_state": ins.excluded.degradation_state,
                "scope_kind": ins.excluded.scope_kind,
                "scope_json": ins.excluded.scope_json,
                "detail_json": ins.excluded.detail_json,
                "source": ins.excluded.source,
                "active": ins.excluded.active,
                "updated_at": datetime.now(tz=UTC),
            },
        )
    )


def failure_case_public_dict(row: CortexCanonicalFailureCase) -> dict[str, Any]:
    return {
        "gap_id": row.gap_id,
        "tenant_id": str(row.tenant_id),
        "failure_class": row.failure_class,
        "degradation_state": row.degradation_state,
        "scope_kind": row.scope_kind,
        "scope_json": dict(row.scope_json),
        "detail_json": dict(row.detail_json),
        "source": row.source,
        "active": row.active,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def remediation_validation_public_dict(row: CortexCanonicalRemediationValidation) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": str(row.tenant_id),
        "failure_case_gap_id": row.failure_case_gap_id,
        "remediation_class": row.remediation_class,
        "dry_run": row.dry_run,
        "confirm_execution": row.confirm_execution,
        "payload_json": dict(row.payload_json),
        "result_status": row.result_status,
        "result_detail_json": dict(row.result_detail_json),
        "created_at": row.created_at,
    }


def record_transform_materialize_failure(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    raw_record_id: int,
    message: str,
    source: str = "admin_transform_materialize",
) -> str:
    gid = _gap_id("transform_materialize_error", str(tenant_id), bundle_id, str(raw_record_id))
    now = datetime.now(tz=UTC)
    scope_json: dict[str, Any] = {"bundle_id": bundle_id, "raw_record_id": raw_record_id}
    raw = session.scalars(
        select(RawIngestionRecord).where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.id == raw_record_id,
        )
    ).first()
    if raw is not None:
        scope_json["connector"] = str(raw.connector or "")
        scope_json["resource_type"] = str(raw.resource_type or "")
        ext = raw.external_id
        if isinstance(ext, str) and ext.strip():
            scope_json["external_id"] = ext.strip()[:512]
        api_ep = raw.api_endpoint
        if isinstance(api_ep, str) and api_ep.strip():
            scope_json["api_endpoint"] = api_ep.strip()[:512]
    _upsert_failure_case(
        session,
        {
            "gap_id": gid,
            "tenant_id": tenant_id,
            "failure_class": "transform_materialize_error",
            "degradation_state": "partial",
            "scope_kind": "single_raw_materialization",
            "scope_json": scope_json,
            "detail_json": {"message": message},
            "source": source,
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
    )
    return gid


def deactivate_transform_materialize_failure_case(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    raw_record_id: int,
) -> None:
    """When materialization succeeds, close the matching transform_materialize_error row if present."""
    gid = _gap_id("transform_materialize_error", str(tenant_id), bundle_id, str(raw_record_id))
    row = session.get(CortexCanonicalFailureCase, gid)
    if row is None or row.tenant_id != tenant_id:
        return
    if row.failure_class != "transform_materialize_error" or not row.active:
        return
    row.active = False
    row.updated_at = datetime.now(tz=UTC)


def sync_replay_job_into_canonical_failure_cases(session: Session, *, job: Any) -> None:
    """Upsert failure row when a completed replay job has forbidden divergence (C3/C4/C5)."""
    if job.status != "completed":
        return
    summary = job.summary_json if isinstance(job.summary_json, dict) else {}
    counts = summary.get("counts_by_divergence_class")
    if not isinstance(counts, dict):
        return
    forbidden = sum(int(counts.get(k, 0) or 0) for k in FORBIDDEN_REPLAY_DIVERGENCE)
    gid = _gap_id("replay_forbidden_divergence", str(job.tenant_id), str(job.id))
    now = datetime.now(tz=UTC)
    if forbidden <= 0:
        _upsert_failure_case(
            session,
            {
                "gap_id": gid,
                "tenant_id": job.tenant_id,
                "failure_class": "replay_forbidden_divergence",
                "degradation_state": "degraded",
                "scope_kind": "replay_job",
                "scope_json": {"replay_job_id": str(job.id)},
                "detail_json": {
                    "counts_by_divergence_class": dict(counts),
                    "note": "cleared_no_forbidden_classes",
                },
                "source": "replay_runtime",
                "active": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        return
    _upsert_failure_case(
        session,
        {
            "gap_id": gid,
            "tenant_id": job.tenant_id,
            "failure_class": "replay_forbidden_divergence",
            "degradation_state": "unverifiable",
            "scope_kind": "replay_job",
            "scope_json": {"replay_job_id": str(job.id), "pinned_bundle_id": job.pinned_bundle_id},
            "detail_json": {
                "counts_by_divergence_class": dict(counts),
                "dry_run": bool(job.dry_run),
                "job_kind": job.job_kind,
            },
            "source": "replay_runtime",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
    )


def record_replay_job_execution_failed(session: Session, *, job: Any, error: str) -> None:
    gid = _gap_id("replay_job_failed", str(job.tenant_id), str(job.id))
    now = datetime.now(tz=UTC)
    _upsert_failure_case(
        session,
        {
            "gap_id": gid,
            "tenant_id": job.tenant_id,
            "failure_class": "replay_job_failed",
            "degradation_state": "degraded",
            "scope_kind": "replay_job",
            "scope_json": {"replay_job_id": str(job.id)},
            "detail_json": {"error": error[:4000]},
            "source": "replay_runtime",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
    )


def _append_remediation_validation(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    failure_case_gap_id: str | None,
    remediation_class: str,
    dry_run: bool,
    confirm_execution: bool,
    payload_json: dict[str, Any],
    result_status: str,
    result_detail_json: dict[str, Any],
) -> CortexCanonicalRemediationValidation:
    row = CortexCanonicalRemediationValidation(
        tenant_id=tenant_id,
        failure_case_gap_id=failure_case_gap_id,
        remediation_class=remediation_class,
        dry_run=dry_run,
        confirm_execution=confirm_execution,
        payload_json=payload_json,
        result_status=result_status,
        result_detail_json=result_detail_json,
    )
    session.add(row)
    session.flush()
    return row


def sync_canonical_failure_cases(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    rows = list(
        session.scalars(
            select(CortexCanonicalFailureCase)
            .where(
                CortexCanonicalFailureCase.tenant_id == tenant_id,
                CortexCanonicalFailureCase.active.is_(True),
            )
            .order_by(CortexCanonicalFailureCase.updated_at.desc())
            .limit(250)
        ).all()
    )
    classes = Counter(r.failure_class for r in rows)
    recent_val = list(
        session.scalars(
            select(CortexCanonicalRemediationValidation)
            .where(CortexCanonicalRemediationValidation.tenant_id == tenant_id)
            .order_by(CortexCanonicalRemediationValidation.created_at.desc())
            .limit(20)
        ).all()
    )
    return {
        "failure_remediation_runtime_schema_version": FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "active_failure_count": len(rows),
        "active_failure_classes": dict(classes),
        "cases": [failure_case_public_dict(r) for r in rows],
        "recent_remediation_validations": [
            remediation_validation_public_dict(r) for r in recent_val
        ],
    }


def validate_canonical_remediation(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    remediation_class: str,
    dry_run: bool,
    confirm_execution: bool,
    failure_case_gap_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Policy-gated remediation: scoped rebuild runs replay; ambiguity triage is ledger-only ack."""
    if remediation_class == "ambiguity_triage_ack":
        detail = {
            "note": "operator_ack_schedules_mapping_workflow_only",
            "payload": dict(payload),
        }
        row = _append_remediation_validation(
            session,
            tenant_id=tenant_id,
            failure_case_gap_id=failure_case_gap_id,
            remediation_class=remediation_class,
            dry_run=True,
            confirm_execution=False,
            payload_json=dict(payload),
            result_status="pass",
            result_detail_json=detail,
        )
        return {
            "tenant_id": str(tenant_id),
            "remediation_class": remediation_class,
            "validation": remediation_validation_public_dict(row),
        }

    if remediation_class != "scoped_rebuild":
        row = _append_remediation_validation(
            session,
            tenant_id=tenant_id,
            failure_case_gap_id=failure_case_gap_id,
            remediation_class=remediation_class,
            dry_run=dry_run,
            confirm_execution=confirm_execution,
            payload_json=dict(payload),
            result_status="failed",
            result_detail_json={"reason": "unknown_remediation_class"},
        )
        return {
            "tenant_id": str(tenant_id),
            "remediation_class": remediation_class,
            "validation": remediation_validation_public_dict(row),
        }

    if not dry_run and not confirm_execution:
        row = _append_remediation_validation(
            session,
            tenant_id=tenant_id,
            failure_case_gap_id=failure_case_gap_id,
            remediation_class=remediation_class,
            dry_run=False,
            confirm_execution=False,
            payload_json=dict(payload),
            result_status="failed",
            result_detail_json={"reason": "confirm_execution_required_for_non_dry_run"},
        )
        return {
            "tenant_id": str(tenant_id),
            "remediation_class": remediation_class,
            "validation": remediation_validation_public_dict(row),
        }

    trust = _tenant_trust_state(session, tenant_id=tenant_id)
    if trust in BLOCKING_TRUST_STATES:
        row = _append_remediation_validation(
            session,
            tenant_id=tenant_id,
            failure_case_gap_id=failure_case_gap_id,
            remediation_class=remediation_class,
            dry_run=dry_run,
            confirm_execution=confirm_execution,
            payload_json=dict(payload),
            result_status="blocked",
            result_detail_json={
                "reason": "phase02_trust_substrate_blocks_canonical_remediation",
                "trust_state": trust,
            },
        )
        return {
            "tenant_id": str(tenant_id),
            "remediation_class": remediation_class,
            "validation": remediation_validation_public_dict(row),
        }

    pinned_bundle_id = str(payload.get("pinned_bundle_id") or "")
    raw_ids_raw = payload.get("raw_record_ids")
    if not pinned_bundle_id or not isinstance(raw_ids_raw, list):
        row = _append_remediation_validation(
            session,
            tenant_id=tenant_id,
            failure_case_gap_id=failure_case_gap_id,
            remediation_class=remediation_class,
            dry_run=dry_run,
            confirm_execution=confirm_execution,
            payload_json=dict(payload),
            result_status="failed",
            result_detail_json={"reason": "pinned_bundle_id_and_raw_record_ids_required"},
        )
        return {
            "tenant_id": str(tenant_id),
            "remediation_class": remediation_class,
            "validation": remediation_validation_public_dict(row),
        }
    try:
        raw_record_ids = [int(x) for x in raw_ids_raw]
    except (TypeError, ValueError):
        row = _append_remediation_validation(
            session,
            tenant_id=tenant_id,
            failure_case_gap_id=failure_case_gap_id,
            remediation_class=remediation_class,
            dry_run=dry_run,
            confirm_execution=confirm_execution,
            payload_json=dict(payload),
            result_status="failed",
            result_detail_json={"reason": "raw_record_ids_must_be_integers"},
        )
        return {
            "tenant_id": str(tenant_id),
            "remediation_class": remediation_class,
            "validation": remediation_validation_public_dict(row),
        }

    job_kind = str(payload.get("job_kind") or "rebuild")
    if job_kind not in ("rebuild", "regeneration"):
        job_kind = "rebuild"
    source_bundle_id = payload.get("source_bundle_id")
    src = str(source_bundle_id) if source_bundle_id else None

    from vector.domains.cortex.canonical import replay_runtime as _replay

    try:
        job = _replay.execute_canonical_replay_job(
            session,
            tenant_id=tenant_id,
            pinned_bundle_id=pinned_bundle_id,
            job_kind=job_kind,  # type: ignore[arg-type]
            raw_record_ids=raw_record_ids,
            source_bundle_id=src,
            dry_run=dry_run,
        )
    except _replay.ReplayJobError as exc:
        row = _append_remediation_validation(
            session,
            tenant_id=tenant_id,
            failure_case_gap_id=failure_case_gap_id,
            remediation_class=remediation_class,
            dry_run=dry_run,
            confirm_execution=confirm_execution,
            payload_json=dict(payload),
            result_status="failed",
            result_detail_json={"reason": "replay_job_parameter_error", "error": str(exc)},
        )
        return {
            "tenant_id": str(tenant_id),
            "remediation_class": remediation_class,
            "validation": remediation_validation_public_dict(row),
        }

    job_full = _replay.get_replay_job(session, tenant_id=tenant_id, job_id=job.id)
    assert job_full is not None
    row = _append_remediation_validation(
        session,
        tenant_id=tenant_id,
        failure_case_gap_id=failure_case_gap_id,
        remediation_class=remediation_class,
        dry_run=dry_run,
        confirm_execution=confirm_execution,
        payload_json=dict(payload),
        result_status="pass",
        result_detail_json={"replay_job": _replay.replay_job_public_dict(job_full)},
    )
    return {
        "tenant_id": str(tenant_id),
        "remediation_class": remediation_class,
        "validation": remediation_validation_public_dict(row),
    }
