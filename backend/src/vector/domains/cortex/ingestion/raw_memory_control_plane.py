"""Phase 02 Step 9 — runtime memory control-plane aggregation."""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Any, Literal, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.raw_memory_enforcement import build_enforcement_summary

_ModeLit = Literal["observe", "progressive", "strict"]
from vector.domains.cortex.ingestion.raw_memory_failure_recovery import sync_raw_memory_failure_cases
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_memory_archive_catalog import RawMemoryArchiveCatalog
from vector.infrastructure.db.models.raw_memory_failure_case import RawMemoryFailureCase
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex
from vector.infrastructure.db.models.raw_memory_recovery_validation import RawMemoryRecoveryValidation
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex


def build_raw_memory_control_plane(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    verification_payload: dict[str, Any],
) -> dict[str, Any]:
    verification = verification_payload
    trust = (
        verification.get("raw_memory_trust", {}).get("annotation")
        if isinstance(verification.get("raw_memory_trust"), dict)
        else None
    )
    trust = trust if isinstance(trust, dict) else {}
    phase_closure = verification.get("raw_memory_phase_closure") if isinstance(verification, dict) else {}
    phase_closure = phase_closure if isinstance(phase_closure, dict) else {}
    enforcement_mode = str(verification.get("enforcement_mode", "progressive"))
    mode_norm = enforcement_mode if enforcement_mode in {"observe", "progressive", "strict"} else "progressive"
    enforcement = build_enforcement_summary(
        trust_annotation=trust,
        phase_closure=phase_closure,
        mode=cast(_ModeLit, mode_norm),
    )

    failures_sync = sync_raw_memory_failure_cases(session, tenant_id)
    active_failures = list(
        session.scalars(
            select(RawMemoryFailureCase).where(
                RawMemoryFailureCase.tenant_id == tenant_id,
                RawMemoryFailureCase.active.is_(True),
            )
        ).all()
    )
    failure_classes = Counter(c.failure_class for c in active_failures)

    replay_runs = list(
        session.scalars(
            select(IngestionRun)
            .where(
                IngestionRun.tenant_id == tenant_id,
                IngestionRun.replay_mode.is_(True),
            )
            .order_by(IngestionRun.started_at.desc())
            .limit(25)
        ).all()
    )

    lineage_count = int(
        session.scalar(
            select(func.count())
            .select_from(RawMemoryLineageIndex)
            .where(RawMemoryLineageIndex.tenant_id == tenant_id)
        )
        or 0
    )
    revision_count = int(
        session.scalar(
            select(func.count())
            .select_from(RawMemoryRevisionIndex)
            .where(RawMemoryRevisionIndex.tenant_id == tenant_id)
        )
        or 0
    )
    tier_counts = {
        str(tier): int(n)
        for tier, n in session.execute(
            select(RawMemoryArchiveCatalog.storage_tier, func.count())
            .where(RawMemoryArchiveCatalog.tenant_id == tenant_id)
            .group_by(RawMemoryArchiveCatalog.storage_tier)
        ).all()
    }
    latest_recovery = session.scalar(
        select(RawMemoryRecoveryValidation)
        .where(RawMemoryRecoveryValidation.tenant_id == tenant_id)
        .order_by(RawMemoryRecoveryValidation.created_at.desc(), RawMemoryRecoveryValidation.id.desc())
        .limit(1)
    )

    crit_raw = verification.get("raw_memory_critical_integrity")
    crit = crit_raw if isinstance(crit_raw, dict) else {}
    op_raw = verification.get("raw_memory_operational_trust_proof")
    op = op_raw if isinstance(op_raw, dict) else {}

    checklist = [
        {
            "id": "replay_trust_status",
            "passed": bool(verification.get("raw_memory_replay", {}).get("passed")),
            "detail": verification.get("raw_memory_replay", {}).get("state"),
        },
        {
            "id": "provenance_continuity_status",
            "passed": bool(verification.get("raw_memory_persistence", {}).get("passed")),
            "detail": verification.get("raw_memory_persistence", {}).get("state"),
        },
        {
            "id": "revision_continuity_status",
            "passed": bool(verification.get("raw_memory_temporal", {}).get("passed")),
            "detail": verification.get("raw_memory_temporal", {}).get("state"),
        },
        {
            "id": "reconstruction_trust_status",
            "passed": bool(verification.get("raw_memory_trust", {}).get("passed")),
            "detail": trust.get("trust_state"),
        },
        {
            "id": "corruption_recovery_status",
            "passed": bool(verification.get("raw_memory_failure_recovery", {}).get("passed")),
            "detail": (
                latest_recovery.status
                if latest_recovery is not None
                else "no_recovery_validation_yet"
            ),
        },
        {
            "id": "queryability_availability_status",
            "passed": bool(verification.get("raw_memory_query", {}).get("passed")),
            "detail": verification.get("raw_memory_query", {}).get("state"),
        },
        {
            "id": "critical_pointer_integrity_status",
            "passed": (
                bool(crit.get("passed"))
                if isinstance(crit_raw, dict)
                else True
            ),
            "detail": crit.get("state") if isinstance(crit_raw, dict) else "not_run",
        },
        {
            "id": "operational_trust_proof_status",
            "passed": bool(op.get("passed")) if isinstance(op_raw, dict) else True,
            "detail": op.get("state") if isinstance(op_raw, dict) else "not_run",
        },
    ]

    actions = [
        {
            "id": "run_recovery_validation",
            "method": "POST",
            "path": f"/admin/tenants/{tenant_id}/cortex/memory/recovery/validate",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "recomputes derived indexes/catalog and validates recoverability state",
            "enforcement": enforcement["decisions"]["recovery_validate"],
        },
        {
            "id": "run_retention_dry_run",
            "method": "POST",
            "path": f"/admin/tenants/{tenant_id}/cortex/memory/retention/apply",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "computes archive/delete candidates without mutating evidence",
            "enforcement": enforcement["decisions"]["retention_apply"],
        },
        {
            "id": "run_failure_sync",
            "method": "GET",
            "path": f"/admin/tenants/{tenant_id}/cortex/memory/failures",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "refreshes failure-class registry and continuity gaps",
            "enforcement": enforcement["decisions"]["recovery_validate"],
        },
        {
            "id": "run_memory_verification",
            "method": "GET",
            "path": f"/admin/tenants/{tenant_id}/cortex/ingestion/verification",
            "safe": True,
            "scope": "tenant",
            "expected_impact": "recomputes gate status for raw memory trust closure",
            "enforcement": enforcement["decisions"]["recovery_validate"],
        },
    ]

    vt_raw = verification.get("phase02_verification_truth")
    vt = vt_raw if isinstance(vt_raw, dict) else {}
    _pq_raw = vt.get("proof_quality")
    pq = _pq_raw if isinstance(_pq_raw, dict) else {}
    _fr_raw = vt.get("freshness")
    fr = _fr_raw if isinstance(_fr_raw, dict) else {}
    proof_primary = pq.get("primary")
    freshness_lbl = fr.get("label")

    crit_passed = bool(crit.get("passed")) if crit else None
    crit_state = crit.get("state") if crit else None
    op_passed = bool(op.get("passed")) if op else None
    op_state = op.get("state") if op else None

    return {
        "tenant_id": str(tenant_id),
        "health_overview": {
            "trust_state": trust.get("trust_state", "unverifiable"),
            "severity": trust.get("severity", "S2"),
            "replay_state": trust.get("replay", {}).get("state"),
            "reconstruction_state": trust.get("reconstruction", {}).get("state"),
            "provenance_state": trust.get("provenance", {}).get("state"),
            "continuity_gap_count": len(trust.get("continuity_gaps", [])),
            "active_failure_count": len(active_failures),
            "active_failure_classes": dict(failure_classes),
            "latest_recovery_validation": (
                {
                    "status": latest_recovery.status,
                    "created_at": latest_recovery.created_at.isoformat(),
                    "apply_repairs": latest_recovery.apply_repairs,
                }
                if latest_recovery is not None
                else None
            ),
            "blocking": trust.get("blocking", {}),
            "state_reason_codes": trust.get("state_reason_codes", []),
            "proof_quality_primary": proof_primary,
            "verification_freshness": freshness_lbl,
            **(
                {
                    "critical_integrity_passed": crit_passed,
                    "critical_integrity_state": crit_state,
                }
                if crit
                else {}
            ),
            **(
                {
                    "operational_trust_passed": op_passed,
                    "operational_trust_state": op_state,
                }
                if op
                else {}
            ),
        },
        "inspectors": {
            "replay_inspector": {
                "jobs_count": len(replay_runs),
                "active_jobs": sum(1 for r in replay_runs if r.status == "RUNNING"),
                "failed_jobs": sum(1 for r in replay_runs if r.status == "FAILED"),
                "latest_jobs": [
                    {
                        "run_id": str(r.id),
                        "connector": r.connector,
                        "status": r.status,
                        "replay_job_id": str(r.replay_job_id) if r.replay_job_id else None,
                        "replay_version": r.replay_version,
                        "started_at": r.started_at.isoformat() if r.started_at else None,
                        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                    }
                    for r in replay_runs[:10]
                ],
            },
            "provenance_explorer": {
                "lineage_rows": lineage_count,
                "active_failure_classes": dict(failure_classes),
            },
            "temporal_reconstruction_inspector": {
                "revision_rows": revision_count,
                "continuity_gaps": trust.get("continuity_gaps", []),
            },
            "corruption_continuity_inspector": {
                "active_failure_count": len(active_failures),
                "active_failures": [
                    {
                        "gap_id": c.gap_id,
                        "failure_class": c.failure_class,
                        "gap_type": c.gap_type,
                        "trust_state_impact": c.trust_state_impact,
                        "recoverability_class": c.recoverability_class,
                        "recovery_status": c.recovery_status,
                    }
                    for c in active_failures[:50]
                ],
            },
            "archive_storage_inspector": {
                "tier_counts": tier_counts,
            },
        },
        "verification_checklist": {
            "passed": all(item["passed"] for item in checklist),
            "items": checklist,
        },
        "phase_closure": (
            dict(verification.get("raw_memory_phase_closure", {}))
            if isinstance(verification, dict)
            else None
        ),
        "verification_truth": (
            dict(verification["phase02_verification_truth"])
            if isinstance(verification, dict)
            and isinstance(verification.get("phase02_verification_truth"), dict)
            else None
        ),
        "enforcement": enforcement,
        "actions": actions,
        "warnings": {
            "must_not_assume": [
                "healthy does not imply semantic truth",
                "replay-safe does not imply replay-complete provider omniscience",
                "reconstructed does not imply complete objective history",
            ],
            "active_failure_sync": failures_sync,
        },
    }


def verify_phase02_step9_control_plane_contract(
    *,
    control_plane_payload: dict[str, Any],
) -> dict[str, Any]:
    required_top = {
        "tenant_id",
        "health_overview",
        "inspectors",
        "verification_checklist",
        "verification_truth",
        "enforcement",
        "actions",
        "warnings",
    }
    required_health = {
        "trust_state",
        "severity",
        "replay_state",
        "reconstruction_state",
        "provenance_state",
        "continuity_gap_count",
        "active_failure_count",
        "state_reason_codes",
        "blocking",
    }
    required_inspectors = {
        "replay_inspector",
        "provenance_explorer",
        "temporal_reconstruction_inspector",
        "corruption_continuity_inspector",
        "archive_storage_inspector",
    }
    top_ok = required_top.issubset(control_plane_payload.keys())
    health = control_plane_payload.get("health_overview", {})
    inspectors = control_plane_payload.get("inspectors", {})
    checklist = control_plane_payload.get("verification_checklist", {})
    actions = control_plane_payload.get("actions", [])
    health_ok = isinstance(health, dict) and required_health.issubset(health.keys())
    inspectors_ok = isinstance(inspectors, dict) and required_inspectors.issubset(inspectors.keys())
    checklist_ok = isinstance(checklist, dict) and isinstance(checklist.get("items"), list)
    actions_ok = isinstance(actions, list) and len(actions) >= 3
    passed = bool(top_ok and health_ok and inspectors_ok and checklist_ok and actions_ok)
    return {
        "passed": passed,
        "state": "healthy" if passed else "degraded",
        "checks": [
            {"id": "s9_control_plane_top_level_contract", "passed": bool(top_ok)},
            {"id": "s9_memory_health_overview_contract", "passed": bool(health_ok)},
            {"id": "s9_inspector_surfaces_contract", "passed": bool(inspectors_ok)},
            {"id": "s9_verification_checklist_surface", "passed": bool(checklist_ok)},
            {"id": "s9_operator_actions_surface", "passed": bool(actions_ok)},
        ],
    }
