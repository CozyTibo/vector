"""Phase 03 Step 17 — stabilization / economics proof pass (substrate scale + replay probes).

Normative context: `DOCS/cortex/03-canonical/phase-03-implementation-readiness-audit.md`.
"""

from __future__ import annotations

import statistics
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_canonical_ambiguity_record import (
    CortexCanonicalAmbiguityRecord,
)
from vector.infrastructure.db.models.cortex_canonical_provenance_record import (
    CortexCanonicalProvenanceRecord,
)
from vector.infrastructure.db.models.cortex_canonical_replay_job import CortexCanonicalReplayJob
from vector.infrastructure.db.models.cortex_canonical_replay_job_receipt import (
    CortexCanonicalReplayJobReceipt,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_canonical_verification_run import (
    CortexCanonicalVerificationRun,
)
from vector.infrastructure.db.models.cortex_canonical_stabilization_proof_run import (
    CortexCanonicalStabilizationProofRun,
)
from vector.infrastructure.db.models.cortex_mapping_bundle_compatibility import (
    CortexMappingBundleCompatibilityEdge,
)
from vector.infrastructure.db.models.cortex_mapping_bundle_pin import CortexMappingBundlePin
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

STABILIZATION_PROOF_SCHEMA_VERSION: Final[int] = 1

_MAX_REPLAY_SCOPE_HARD_FAIL: Final[int] = 50_000
_AMBIGUITY_EXPLOSION_WARN: Final[int] = 5000


def _median_int(values: list[int]) -> int | None:
    if not values:
        return None
    s = sorted(values)
    return int(statistics.median(s))


def build_stabilization_proof_report(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    raw_count = int(
        session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(RawIngestionRecord.tenant_id == tenant_id)
        )
        or 0
    )
    mat_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        )
        or 0
    )
    prov_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalProvenanceRecord)
            .where(CortexCanonicalProvenanceRecord.tenant_id == tenant_id)
        )
        or 0
    )
    receipt_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalReplayJobReceipt)
            .join(
                CortexCanonicalReplayJob,
                CortexCanonicalReplayJobReceipt.job_id == CortexCanonicalReplayJob.id,
            )
            .where(CortexCanonicalReplayJob.tenant_id == tenant_id)
        )
        or 0
    )

    replay_jobs = list(
        session.scalars(
            select(CortexCanonicalReplayJob)
            .where(CortexCanonicalReplayJob.tenant_id == tenant_id)
            .order_by(CortexCanonicalReplayJob.created_at.desc())
            .limit(40)
        ).all()
    )

    completed = [
        j for j in replay_jobs if j.status == "completed" and j.started_at and j.completed_at
    ]
    durations_ms: list[int] = []
    scope_sizes: list[int] = []
    for j in completed[:25]:
        delta = j.completed_at - j.started_at
        durations_ms.append(int(delta.total_seconds() * 1000))
        scope = j.scope_raw_record_ids or []
        if isinstance(scope, list):
            scope_sizes.append(len(scope))

    max_scope = max(scope_sizes) if scope_sizes else 0
    last_ver = session.scalar(
        select(CortexCanonicalVerificationRun)
        .where(CortexCanonicalVerificationRun.tenant_id == tenant_id)
        .order_by(
            CortexCanonicalVerificationRun.created_at.desc(),
            CortexCanonicalVerificationRun.id.desc(),
        )
        .limit(1)
    )
    cutoff_7d = datetime.now(tz=UTC) - timedelta(days=7)
    ver_7d = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalVerificationRun)
            .where(
                CortexCanonicalVerificationRun.tenant_id == tenant_id,
                CortexCanonicalVerificationRun.created_at >= cutoff_7d,
            )
        )
        or 0
    )

    open_amb = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalAmbiguityRecord)
            .where(
                CortexCanonicalAmbiguityRecord.tenant_id == tenant_id,
                CortexCanonicalAmbiguityRecord.status == "open",
            )
        )
        or 0
    )
    total_amb = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalAmbiguityRecord)
            .where(CortexCanonicalAmbiguityRecord.tenant_id == tenant_id)
        )
        or 0
    )

    pin_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexMappingBundlePin)
            .where(CortexMappingBundlePin.tenant_id == tenant_id)
        )
        or 0
    )
    breaking_edges = int(
        session.scalar(
            select(func.count())
            .select_from(CortexMappingBundleCompatibilityEdge)
            .where(CortexMappingBundleCompatibilityEdge.is_breaking.is_(True))
        )
        or 0
    )

    projection_ratio = (mat_count / raw_count) if raw_count > 0 else None

    substrate_scale = {
        "raw_ingestion_row_count": raw_count,
        "canonical_materialization_row_count": mat_count,
        "canonical_provenance_row_count": prov_count,
        "replay_receipt_row_count": receipt_count,
        "canonical_projection_ratio_vs_raw": projection_ratio,
    }

    replay_economics = {
        "recent_jobs_window": len(replay_jobs),
        "completed_jobs_with_timing_sample": len(completed[:25]),
        "replay_duration_median_ms": _median_int(durations_ms),
        "replay_duration_max_ms": max(durations_ms) if durations_ms else None,
        "replay_scope_max_raw_records_recent_completed": max_scope,
        "replay_scope_sizes_sample_head": scope_sizes[:10],
    }

    verification_continuity = {
        "verification_runs_last_7d": ver_7d,
        "last_verification_run_id": last_ver.id if last_ver else None,
        "last_verification_passed": bool(last_ver.passed) if last_ver else None,
        "last_verification_at": last_ver.created_at.isoformat()
        if last_ver and last_ver.created_at
        else None,
    }

    ambiguity_pressure = {
        "open_ambiguity_records": open_amb,
        "total_ambiguity_records": total_amb,
        "open_ratio": (open_amb / total_amb) if total_amb > 0 else None,
        "explosion_warn_threshold": _AMBIGUITY_EXPLOSION_WARN,
        "explosion_warn": open_amb >= _AMBIGUITY_EXPLOSION_WARN,
    }

    mapping_governance = {
        "tenant_mapping_pin_rows": pin_count,
        "global_breaking_compatibility_edges": breaking_edges,
    }

    bounded_slice = min(200, raw_count)
    reconstruction_slice = {
        "bounded_raw_reconstruction_sample_size": bounded_slice,
        "note": (
            "Deterministic bounded slice for large-tenant reconstruction drill planning; "
            "not a semantic reconstruction."
        ),
    }

    checklist: list[dict[str, Any]] = [
        {
            "id": "substrate_counts_computable",
            "passed": True,
            "severity": "hard_fail",
            "detail": {"raw": raw_count, "materializations": mat_count},
        },
        {
            "id": "provenance_present_when_canonical_projections_exist",
            "passed": mat_count == 0 or prov_count > 0,
            "severity": "hard_fail",
            "detail": {"materializations": mat_count, "provenance_rows": prov_count},
        },
        {
            "id": "replay_scope_within_declared_budget",
            "passed": max_scope <= _MAX_REPLAY_SCOPE_HARD_FAIL,
            "severity": "hard_fail",
            "detail": {"max_scope_raw_records": max_scope, "budget": _MAX_REPLAY_SCOPE_HARD_FAIL},
        },
        {
            "id": "verification_engine_has_prior_run",
            "passed": last_ver is not None,
            "severity": "warn_only",
            "detail": None if last_ver else "no_verification_run_yet",
        },
        {
            "id": "verification_sweep_recency_7d",
            "passed": ver_7d >= 1,
            "severity": "warn_only",
            "detail": {"runs_last_7d": ver_7d},
        },
        {
            "id": "ambiguity_explosion_pressure",
            "passed": open_amb < _AMBIGUITY_EXPLOSION_WARN,
            "severity": "warn_only",
            "detail": ambiguity_pressure,
        },
    ]

    hard_ok = all(bool(x["passed"]) for x in checklist if x.get("severity") == "hard_fail")
    warn_ok = all(bool(x["passed"]) for x in checklist if x.get("severity") == "warn_only")
    # Primary signal: hard gates only (warn-only items track soak / economics pressure).
    overall_passed = bool(hard_ok)

    return {
        "tenant_id": str(tenant_id),
        "stabilization_proof_schema_version": STABILIZATION_PROOF_SCHEMA_VERSION,
        "overall_passed": overall_passed,
        "hard_fail_passed": hard_ok,
        "warn_only_all_passed": warn_ok,
        "proof_checklist": checklist,
        "substrate_scale": substrate_scale,
        "replay_economics": replay_economics,
        "verification_continuity": verification_continuity,
        "ambiguity_pressure": ambiguity_pressure,
        "mapping_governance": mapping_governance,
        "reconstruction_slice": reconstruction_slice,
        "doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-implementation-readiness-audit.md",
            "DOCS/cortex/03-canonical/phase-03-replay-versioning-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-canonical-query-doctrine.md",
        ],
        "warnings": {
            "must_not_assume": [
                "economics probes are substrate-shaped, not predictive cost models",
                "PASS does not certify Phase 03 closure — Step 18 archival pack required",
            ],
        },
    }


def verify_phase03_step17_stabilization_proof_contract(*, report: dict[str, Any]) -> dict[str, Any]:
    required_top = {
        "tenant_id",
        "stabilization_proof_schema_version",
        "overall_passed",
        "hard_fail_passed",
        "warn_only_all_passed",
        "proof_checklist",
        "substrate_scale",
        "replay_economics",
        "verification_continuity",
        "ambiguity_pressure",
        "mapping_governance",
        "reconstruction_slice",
        "warnings",
    }
    required_scale = {"raw_ingestion_row_count", "canonical_materialization_row_count"}
    required_replay = {"recent_jobs_window", "replay_scope_max_raw_records_recent_completed"}
    top_ok = required_top.issubset(report.keys())
    scale = report.get("substrate_scale", {})
    replay = report.get("replay_economics", {})
    chk = report.get("proof_checklist", [])
    scale_ok = isinstance(scale, dict) and required_scale.issubset(scale.keys())
    replay_ok = isinstance(replay, dict) and required_replay.issubset(replay.keys())
    chk_ok = isinstance(chk, list) and len(chk) >= 3
    passed = bool(top_ok and scale_ok and replay_ok and chk_ok)
    return {
        "passed": passed,
        "state": "healthy" if passed else "degraded",
        "checks": [
            {"id": "s17_report_top_level_contract", "passed": bool(top_ok)},
            {"id": "s17_substrate_scale_contract", "passed": bool(scale_ok)},
            {"id": "s17_replay_economics_contract", "passed": bool(replay_ok)},
            {"id": "s17_proof_checklist_contract", "passed": bool(chk_ok)},
        ],
    }


def stabilization_proof_run_public_dict(
    row: CortexCanonicalStabilizationProofRun,
) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": str(row.tenant_id),
        "proof_schema_version": row.proof_schema_version,
        "passed": row.passed,
        "probes_json": dict(row.probes_json),
        "created_at": row.created_at,
    }


def run_stabilization_proof_pass(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    persist: bool = False,
) -> dict[str, Any]:
    """Compute stabilization proof; optionally persist a ledger row (operator audit trail)."""
    report = build_stabilization_proof_report(session, tenant_id)
    out = {**report, "persisted_run_id": None}
    if persist:
        row = CortexCanonicalStabilizationProofRun(
            tenant_id=tenant_id,
            proof_schema_version=STABILIZATION_PROOF_SCHEMA_VERSION,
            passed=bool(report["overall_passed"]),
            probes_json=report,
        )
        session.add(row)
        session.flush()
        out["persisted_run_id"] = row.id
    return out


def list_stabilization_proof_runs(
    session: Session, *, tenant_id: uuid.UUID, limit: int = 20
) -> list[CortexCanonicalStabilizationProofRun]:
    lim = max(1, min(limit, 100))
    return list(
        session.scalars(
            select(CortexCanonicalStabilizationProofRun)
            .where(CortexCanonicalStabilizationProofRun.tenant_id == tenant_id)
            .order_by(
                CortexCanonicalStabilizationProofRun.created_at.desc(),
                CortexCanonicalStabilizationProofRun.id.desc(),
            )
            .limit(lim)
        ).all()
    )
