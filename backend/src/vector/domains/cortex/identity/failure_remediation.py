"""Phase 04 Step 16 — org failure registry + policy-gated remediation (P04-16).

Normative: `DOCS/cortex/04-identity/phase-04-failure-remediation-doctrine.md`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Final, Literal

from sqlalchemy import func, nullslast, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.link_ledger import list_authoritative_temporal_overlap_violations_for_tenant
from vector.infrastructure.db.models.cortex_org_failure_case import CortexOrgFailureCase
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.infrastructure.db.models.cortex_org_link_replay_job_receipt import CortexOrgLinkReplayJobReceipt
from vector.infrastructure.db.models.cortex_org_remediation_validation import CortexOrgRemediationValidation

ORG_FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

OrgRemediationClass = Literal["org_ambiguity_triage_ack", "org_link_replay_retry"]


def _gap_id(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def _upsert_org_failure_case(session: Session, case: dict[str, Any]) -> None:
    tbl = CortexOrgFailureCase.__table__
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


def org_failure_case_public_dict(row: CortexOrgFailureCase) -> dict[str, Any]:
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


def org_remediation_validation_public_dict(row: CortexOrgRemediationValidation) -> dict[str, Any]:
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


def record_org_link_replay_job_failed(session: Session, job: CortexOrgLinkReplayJob, *, error: str | None = None) -> str:
    """Persist a durable org failure row when an org link replay job ends in ``failed``."""
    gid = _gap_id("org_link_replay_job_failed", str(job.tenant_id), str(job.id))
    now = datetime.now(tz=UTC)
    _upsert_org_failure_case(
        session,
        {
            "gap_id": gid,
            "tenant_id": job.tenant_id,
            "failure_class": "org_link_replay_job_failed",
            "degradation_state": "degraded",
            "scope_kind": "org_link_replay_job",
            "scope_json": {"org_link_replay_job_id": str(job.id), "job_kind": job.job_kind},
            "detail_json": {"error": (error or job.error_detail or "")[:4000]},
            "source": "org_link_replay_runtime",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
    )
    return gid


def recompute_org_derived_failure_cases(session: Session, tenant_id: uuid.UUID) -> None:
    """Upsert derived org failure rows from replay jobs + temporal overlap scan (idempotent)."""
    now = datetime.now(tz=UTC)

    failed_jobs = list(
        session.scalars(
            select(CortexOrgLinkReplayJob).where(
                CortexOrgLinkReplayJob.tenant_id == tenant_id,
                CortexOrgLinkReplayJob.status == "failed",
            )
        ).all()
    )
    for job in failed_jobs:
        gid = _gap_id("org_link_replay_job_failed", str(tenant_id), str(job.id))
        _upsert_org_failure_case(
            session,
            {
                "gap_id": gid,
                "tenant_id": tenant_id,
                "failure_class": "org_link_replay_job_failed",
                "degradation_state": "degraded",
                "scope_kind": "org_link_replay_job",
                "scope_json": {"org_link_replay_job_id": str(job.id), "job_kind": job.job_kind},
                "detail_json": {"error": (job.error_detail or "")[:4000]},
                "source": "org_failure_remediation_sync",
                "active": True,
                "created_at": now,
                "updated_at": now,
            },
        )

    completed_jobs = list(
        session.scalars(
            select(CortexOrgLinkReplayJob)
            .where(
                CortexOrgLinkReplayJob.tenant_id == tenant_id,
                CortexOrgLinkReplayJob.status == "completed",
            )
            .order_by(nullslast(CortexOrgLinkReplayJob.completed_at.desc()))
            .limit(5000)
        ).all()
    )
    for job in completed_jobs:
        gid = _gap_id("org_link_replay_missing_receipts", str(tenant_id), str(job.id))
        n = session.scalar(
            select(func.count())
            .select_from(CortexOrgLinkReplayJobReceipt)
            .where(CortexOrgLinkReplayJobReceipt.job_id == job.id)
        )
        rc = int(n or 0)
        if rc == 0:
            _upsert_org_failure_case(
                session,
                {
                    "gap_id": gid,
                    "tenant_id": tenant_id,
                    "failure_class": "org_link_replay_missing_receipts",
                    "degradation_state": "unverifiable",
                    "scope_kind": "org_link_replay_job",
                    "scope_json": {"org_link_replay_job_id": str(job.id), "job_kind": job.job_kind},
                    "detail_json": {"receipt_count": 0, "note": "completed_job_requires_L_class_receipt"},
                    "source": "org_failure_remediation_sync",
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        else:
            _upsert_org_failure_case(
                session,
                {
                    "gap_id": gid,
                    "tenant_id": tenant_id,
                    "failure_class": "org_link_replay_missing_receipts",
                    "degradation_state": "healthy",
                    "scope_kind": "org_link_replay_job",
                    "scope_json": {"org_link_replay_job_id": str(job.id)},
                    "detail_json": {"receipt_count": rc, "note": "cleared_receipts_present"},
                    "source": "org_failure_remediation_sync",
                    "active": False,
                    "created_at": now,
                    "updated_at": now,
                },
            )

    overlaps = list_authoritative_temporal_overlap_violations_for_tenant(session, tenant_id=tenant_id)
    gid_t = _gap_id("org_link_temporal_overlap", str(tenant_id))
    if overlaps:
        _upsert_org_failure_case(
            session,
            {
                "gap_id": gid_t,
                "tenant_id": tenant_id,
                "failure_class": "org_link_temporal_overlap",
                "degradation_state": "conflicting",
                "scope_kind": "tenant_authoritative_link_scan",
                "scope_json": {"tenant_id": str(tenant_id)},
                "detail_json": {
                    "violation_count": len(overlaps),
                    "overlap_pairs": overlaps[:40],
                },
                "source": "org_failure_remediation_sync",
                "active": True,
                "created_at": now,
                "updated_at": now,
            },
        )
    else:
        _upsert_org_failure_case(
            session,
            {
                "gap_id": gid_t,
                "tenant_id": tenant_id,
                "failure_class": "org_link_temporal_overlap",
                "degradation_state": "healthy",
                "scope_kind": "tenant_authoritative_link_scan",
                "scope_json": {"tenant_id": str(tenant_id)},
                "detail_json": {"violation_count": 0, "note": "no_overlaps"},
                "source": "org_failure_remediation_sync",
                "active": False,
                "created_at": now,
                "updated_at": now,
            },
        )


def sync_org_failure_cases(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    recompute_org_derived_failure_cases(session, tenant_id)
    rows = list(
        session.scalars(
            select(CortexOrgFailureCase)
            .where(
                CortexOrgFailureCase.tenant_id == tenant_id,
                CortexOrgFailureCase.active.is_(True),
            )
            .order_by(CortexOrgFailureCase.updated_at.desc())
            .limit(250)
        ).all()
    )
    classes = Counter(r.failure_class for r in rows)
    recent_val = list(
        session.scalars(
            select(CortexOrgRemediationValidation)
            .where(CortexOrgRemediationValidation.tenant_id == tenant_id)
            .order_by(CortexOrgRemediationValidation.created_at.desc())
            .limit(20)
        ).all()
    )
    return {
        "org_failure_remediation_runtime_schema_version": ORG_FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "active_failure_count": len(rows),
        "active_failure_classes": dict(classes),
        "cases": [org_failure_case_public_dict(r) for r in rows],
        "recent_remediation_validations": [org_remediation_validation_public_dict(r) for r in recent_val],
    }


def _append_org_remediation_validation(
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
) -> CortexOrgRemediationValidation:
    row = CortexOrgRemediationValidation(
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


def validate_org_remediation(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    remediation_class: str,
    dry_run: bool,
    confirm_execution: bool,
    failure_case_gap_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Policy-gated org remediation: ambiguity triage ack (ledger-only) or org link replay retry."""
    if remediation_class == "org_ambiguity_triage_ack":
        detail = {"note": "operator_ack_schedules_identity_triage_only", "payload": dict(payload)}
        row = _append_org_remediation_validation(
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
            "validation": org_remediation_validation_public_dict(row),
        }

    if remediation_class != "org_link_replay_retry":
        row = _append_org_remediation_validation(
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
            "validation": org_remediation_validation_public_dict(row),
        }

    if not dry_run and not confirm_execution:
        row = _append_org_remediation_validation(
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
            "validation": org_remediation_validation_public_dict(row),
        }

    job_kind = str(payload.get("job_kind") or "")
    if job_kind not in ("authoritative_replay", "candidate_regen"):
        row = _append_org_remediation_validation(
            session,
            tenant_id=tenant_id,
            failure_case_gap_id=failure_case_gap_id,
            remediation_class=remediation_class,
            dry_run=dry_run,
            confirm_execution=confirm_execution,
            payload_json=dict(payload),
            result_status="failed",
            result_detail_json={"reason": "job_kind_must_be_authoritative_replay_or_candidate_regen"},
        )
        return {
            "tenant_id": str(tenant_id),
            "remediation_class": remediation_class,
            "validation": org_remediation_validation_public_dict(row),
        }

    pinned = str(payload.get("pinned_rule_version") or "").strip() or None
    scope_json = payload.get("scope_json")
    scope = dict(scope_json) if isinstance(scope_json, dict) else {}

    from vector.domains.cortex.identity.org_link_replay_runtime import (
        OrgLinkReplayError,
        execute_org_link_replay_job,
        org_link_replay_job_public_dict,
    )

    try:
        job = execute_org_link_replay_job(
            session,
            tenant_id=tenant_id,
            job_kind=job_kind,  # type: ignore[arg-type]
            pinned_rule_version=pinned,
            dry_run=dry_run,
            scope_json=scope,
        )
    except OrgLinkReplayError as exc:
        row = _append_org_remediation_validation(
            session,
            tenant_id=tenant_id,
            failure_case_gap_id=failure_case_gap_id,
            remediation_class=remediation_class,
            dry_run=dry_run,
            confirm_execution=confirm_execution,
            payload_json=dict(payload),
            result_status="failed",
            result_detail_json={"reason": "org_link_replay_parameter_error", "error": str(exc)},
        )
        return {
            "tenant_id": str(tenant_id),
            "remediation_class": remediation_class,
            "validation": org_remediation_validation_public_dict(row),
        }

    job_snap = json.loads(json.dumps(org_link_replay_job_public_dict(job), default=str))
    row = _append_org_remediation_validation(
        session,
        tenant_id=tenant_id,
        failure_case_gap_id=failure_case_gap_id,
        remediation_class=remediation_class,
        dry_run=dry_run,
        confirm_execution=confirm_execution,
        payload_json=dict(payload),
        result_status="pass",
        result_detail_json={"org_link_replay_job": job_snap},
    )
    return {
        "tenant_id": str(tenant_id),
        "remediation_class": remediation_class,
        "validation": org_remediation_validation_public_dict(row),
    }


def verify_gp04_19_org_failure_registry_sync(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-19 — catalog + derived org failure signals match persisted registry after recompute."""
    catalog_errors: list[str] = []
    if ORG_FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION < 1:
        catalog_errors.append("org_failure_remediation_schema_invalid")

    recompute_org_derived_failure_cases(session, tenant_id=tenant_id)
    session.flush()

    failed_jobs = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLinkReplayJob)
            .where(
                CortexOrgLinkReplayJob.tenant_id == tenant_id,
                CortexOrgLinkReplayJob.status == "failed",
            )
        )
        or 0
    )
    active_failed = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgFailureCase)
            .where(
                CortexOrgFailureCase.tenant_id == tenant_id,
                CortexOrgFailureCase.active.is_(True),
                CortexOrgFailureCase.failure_class == "org_link_replay_job_failed",
            )
        )
        or 0
    )

    missing_ids: list[uuid.UUID] = []
    completed = list(
        session.scalars(
            select(CortexOrgLinkReplayJob)
            .where(
                CortexOrgLinkReplayJob.tenant_id == tenant_id,
                CortexOrgLinkReplayJob.status == "completed",
            )
            .limit(5000)
        ).all()
    )
    for job in completed:
        n = int(
            session.scalar(
                select(func.count())
                .select_from(CortexOrgLinkReplayJobReceipt)
                .where(CortexOrgLinkReplayJobReceipt.job_id == job.id)
            )
            or 0
        )
        if n == 0:
            missing_ids.append(job.id)
    active_missing = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgFailureCase)
            .where(
                CortexOrgFailureCase.tenant_id == tenant_id,
                CortexOrgFailureCase.active.is_(True),
                CortexOrgFailureCase.failure_class == "org_link_replay_missing_receipts",
            )
        )
        or 0
    )

    overlaps = list_authoritative_temporal_overlap_violations_for_tenant(session, tenant_id=tenant_id)
    active_overlap = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgFailureCase)
            .where(
                CortexOrgFailureCase.tenant_id == tenant_id,
                CortexOrgFailureCase.active.is_(True),
                CortexOrgFailureCase.failure_class == "org_link_temporal_overlap",
            )
        )
        or 0
    )

    drift: list[str] = []
    if failed_jobs != active_failed:
        drift.append(f"failed_job_count_mismatch:jobs={failed_jobs} active_cases={active_failed}")
    if len(missing_ids) != active_missing:
        drift.append(f"missing_receipt_mismatch:jobs={len(missing_ids)} active_cases={active_missing}")
    want_overlap = 1 if overlaps else 0
    if want_overlap != active_overlap:
        drift.append(f"temporal_overlap_mismatch:want_active={want_overlap} active_cases={active_overlap}")

    passed = len(catalog_errors) == 0 and len(drift) == 0
    return {
        "id": "G-P04-19",
        "name": "org_failure_registry_sync_completeness",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "catalog_errors": catalog_errors,
            "tenant_id": str(tenant_id),
            "failed_org_replay_jobs": failed_jobs,
            "active_org_link_replay_job_failed_cases": active_failed,
            "completed_jobs_missing_receipts": len(missing_ids),
            "active_missing_receipt_cases": active_missing,
            "temporal_overlap_violations": len(overlaps),
            "active_temporal_overlap_cases": active_overlap,
            "drift": drift,
            "expected_derived_failure_classes": sorted(
                {"org_link_replay_job_failed", "org_link_replay_missing_receipts", "org_link_temporal_overlap"}
            ),
        },
    }
