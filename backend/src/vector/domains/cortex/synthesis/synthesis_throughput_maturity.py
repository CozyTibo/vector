"""Phase 08 / 08.5 — synthesis throughput maturity (**G-P085-SYN-03**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-synthesis-activation-doctrine.md`` §Throughput.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    SYNTHESIS_COVERAGE_THRESHOLD_PERCENT_V1,
    count_synthesis_eligible_scopes_v1,
    count_synthesis_synthesized_scopes_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_activation_audit import (
    CortexSynthesisActivationAudit,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

GP085_SYN03_GATE_ID_V1: Final[str] = "G-P085-SYN-03"

METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1: Final[str] = "synthesis_jobs_completed_per_day"
METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1: Final[str] = "synthesis_scope_coverage_percent"
METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1: Final[str] = "synthesis_activation_audit_empty_rate"

SYNTHESIS_THROUGHPUT_METRIC_IDS_V1: Final[tuple[str, ...]] = (
    METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1,
    METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1,
    METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1,
)

SYNTHESIS_MATURITY_SYN0_V1: Final[str] = "SYN0"
SYNTHESIS_MATURITY_SYN1_V1: Final[str] = "SYN1"
SYNTHESIS_MATURITY_SYN2_V1: Final[str] = "SYN2"
SYNTHESIS_MATURITY_SYN3_V1: Final[str] = "SYN3"

SYNTHESIS_STAGE_OMISSION_THROUGHPUT_GAP_V1: Final[str] = "synthesis_throughput_gap"
SYNTHESIS_STAGE_OMISSION_ACTIVATION_AUDIT_EMPTY_V1: Final[str] = "synthesis_activation_audit_empty"

_DEFAULT_JOBS_PER_DAY_FLOOR_V1: Final[int] = 1
_DEFAULT_AUDIT_WINDOW_HOURS_V1: Final[int] = 168
_DEFAULT_AUDIT_EMPTY_RATE_MAX_V1: Final[float] = 5.0


def get_synthesis_throughput_policy_v1() -> dict[str, Any]:
    try:
        from vector.settings import get_settings

        cfg = get_settings()
        return {
            "jobs_per_day_floor": max(
                0,
                int(cfg.cortex_synthesis_throughput_jobs_per_day_floor),
            ),
            "scope_coverage_target_percent": float(
                cfg.cortex_synthesis_scope_coverage_target_percent
            ),
            "activation_audit_empty_rate_max_percent": float(
                cfg.cortex_synthesis_activation_audit_empty_rate_max_percent
            ),
            "activation_audit_window_hours": max(
                1,
                int(cfg.cortex_synthesis_activation_audit_window_hours),
            ),
        }
    except Exception:  # noqa: BLE001
        return {
            "jobs_per_day_floor": _DEFAULT_JOBS_PER_DAY_FLOOR_V1,
            "scope_coverage_target_percent": float(SYNTHESIS_COVERAGE_THRESHOLD_PERCENT_V1),
            "activation_audit_empty_rate_max_percent": _DEFAULT_AUDIT_EMPTY_RATE_MAX_V1,
            "activation_audit_window_hours": _DEFAULT_AUDIT_WINDOW_HOURS_V1,
        }


def count_synthesis_jobs_completed_per_day_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> int:
    since = datetime.now(tz=UTC) - timedelta(hours=24)
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status == "completed",
                CortexSynthesisJob.created_at >= since,
            )
        )
        or 0
    )


def compute_synthesis_scope_coverage_percent_v1(
    *,
    eligible_scopes: int,
    synthesized_scopes: int,
) -> float:
    if eligible_scopes <= 0:
        return 100.0 if synthesized_scopes > 0 else 0.0
    return round(min(100.0, max(0.0, float(synthesized_scopes) / float(eligible_scopes) * 100.0)), 2)


def compute_synthesis_activation_audit_empty_rate_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    window_hours: int | None = None,
) -> dict[str, Any]:
    """Empty activation rate from ``cortex_synthesis_activation_audits`` in rolling window."""
    policy = get_synthesis_throughput_policy_v1()
    hours = int(window_hours or policy["activation_audit_window_hours"])
    since = datetime.now(tz=UTC) - timedelta(hours=hours)
    rows = list(
        session.scalars(
            select(CortexSynthesisActivationAudit)
            .where(
                CortexSynthesisActivationAudit.tenant_id == tenant_id,
                CortexSynthesisActivationAudit.created_at >= since,
            )
            .order_by(CortexSynthesisActivationAudit.created_at.desc())
        ).all()
    )
    total = len(rows)
    empty = sum(1 for row in rows if row.empty_scope_reason)
    activations_with_scopes = sum(1 for row in rows if int(row.scopes_generated or 0) > 0)
    jobs_completed_sum = sum(int(row.synthesis_jobs_completed or 0) for row in rows)
    rate = round((float(empty) / float(total)) * 100.0, 2) if total > 0 else 0.0
    return {
        "audit_window_hours": hours,
        "activation_audit_total": total,
        "activation_audit_empty_count": empty,
        "activation_audits_with_scopes": activations_with_scopes,
        "activation_jobs_completed_sum": jobs_completed_sum,
        METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1: rate,
    }


def evaluate_synthesis_throughput_targets_v1(
    *,
    jobs_completed_per_day: int,
    scope_coverage_percent: float,
    activation_audit_empty_rate: float,
    eligible_scopes: int,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pol = dict(policy or get_synthesis_throughput_policy_v1())
    floor = int(pol["jobs_per_day_floor"])
    coverage_target = float(pol["scope_coverage_target_percent"])
    empty_max = float(pol["activation_audit_empty_rate_max_percent"])

    jobs_meets = jobs_completed_per_day >= floor
    coverage_meets = scope_coverage_percent >= coverage_target
    empty_meets = eligible_scopes <= 0 or activation_audit_empty_rate <= empty_max

    return {
        "jobs_per_day_floor": floor,
        "scope_coverage_target_percent": coverage_target,
        "activation_audit_empty_rate_max_percent": empty_max,
        "jobs_per_day_meets_floor": jobs_meets,
        "scope_coverage_meets_target": coverage_meets,
        "audit_empty_rate_within_limit": empty_meets,
        "all_throughput_targets_met": jobs_meets and coverage_meets and empty_meets,
    }


def classify_synthesis_throughput_maturity_v1(
    *,
    jobs_completed_per_day: int,
    scope_coverage_percent: float,
    targets: Mapping[str, Any],
) -> str:
    if jobs_completed_per_day <= 0 and scope_coverage_percent <= 0.0:
        return SYNTHESIS_MATURITY_SYN0_V1
    if bool(targets.get("all_throughput_targets_met")):
        return SYNTHESIS_MATURITY_SYN3_V1
    if scope_coverage_percent >= 40.0 or jobs_completed_per_day > 0:
        return SYNTHESIS_MATURITY_SYN2_V1
    return SYNTHESIS_MATURITY_SYN1_V1


def derive_synthesis_throughput_substrate_state_v1(
    *,
    targets: Mapping[str, Any],
    eligible_scopes: int,
    scope_coverage_percent: float,
) -> str:
    if eligible_scopes > 0 and scope_coverage_percent < 40.0:
        return "degraded"
    if not targets.get("audit_empty_rate_within_limit") and eligible_scopes > 0:
        return "degraded"
    if not targets.get("jobs_per_day_meets_floor") and eligible_scopes > 0:
        return "degraded"
    if not targets.get("all_throughput_targets_met") and eligible_scopes > 0:
        return "degraded"
    return "healthy"


def compute_synthesis_throughput_metrics_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Tenant synthesis throughput snapshot (**G-P085-SYN-03**)."""
    policy = get_synthesis_throughput_policy_v1()
    scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
    synth = count_synthesis_synthesized_scopes_v1(session, tenant_id=tenant_id)
    eligible = int(scope.get("eligible_scopes") or 0)
    synthesized = int(synth.get("synthesized_scopes") or 0)
    jobs_day = count_synthesis_jobs_completed_per_day_v1(session, tenant_id=tenant_id)
    coverage = compute_synthesis_scope_coverage_percent_v1(
        eligible_scopes=eligible,
        synthesized_scopes=synthesized,
    )
    audit_stats = compute_synthesis_activation_audit_empty_rate_v1(session, tenant_id=tenant_id)
    empty_rate = float(audit_stats[METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1])

    targets = evaluate_synthesis_throughput_targets_v1(
        jobs_completed_per_day=jobs_day,
        scope_coverage_percent=coverage,
        activation_audit_empty_rate=empty_rate,
        eligible_scopes=eligible,
        policy=policy,
    )
    maturity = classify_synthesis_throughput_maturity_v1(
        jobs_completed_per_day=jobs_day,
        scope_coverage_percent=coverage,
        targets=targets,
    )
    substrate_state = derive_synthesis_throughput_substrate_state_v1(
        targets=targets,
        eligible_scopes=eligible,
        scope_coverage_percent=coverage,
    )

    metrics = {
        METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1: jobs_day,
        METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1: coverage,
        METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1: empty_rate,
        "eligible_scopes": eligible,
        "synthesized_scopes": synthesized,
        "activation_audit_total": audit_stats["activation_audit_total"],
        "activation_audit_empty_count": audit_stats["activation_audit_empty_count"],
        "jobs_per_day_meets_floor": targets["jobs_per_day_meets_floor"],
        "scope_coverage_meets_target": targets["scope_coverage_meets_target"],
        "audit_empty_rate_within_limit": targets["audit_empty_rate_within_limit"],
        "all_throughput_targets_met": targets["all_throughput_targets_met"],
    }

    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_SYN03_GATE_ID_V1,
        "synthesis_maturity_class": maturity,
        "substrate_state": substrate_state,
        "throughput_policy": policy,
        "throughput_targets": targets,
        "activation_audit_stats": audit_stats,
        "metrics": metrics,
    }


def _refresh_stage_envelope_receipt_digest_v1(stage: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(stage)
    payload = {
        "stage_id": out.get("stage_id"),
        "substrate_state": out.get("substrate_state"),
        "total_objects": out.get("total_objects"),
        "processed_count": out.get("processed_count"),
        "omission_classes": out.get("omission_classes"),
        "metrics": out.get("metrics"),
    }
    out["receipt_digest"] = hash_reasoning_canonical_json_sha256_v1(payload)
    return out


def apply_synthesis_throughput_maturity_to_stage_v1(
    stage: Mapping[str, Any],
    *,
    throughput: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge **G-P085-SYN-03** throughput metrics into synthesis completeness stage."""
    out = dict(stage)
    metrics = dict(out.get("metrics") or {})
    tm = dict(throughput.get("metrics") or {})
    metrics.update(
        {
            METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1: tm[METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1],
            METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1: tm[METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1],
            METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1: tm[
                METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1
            ],
            "synthesis_maturity_class": throughput.get("synthesis_maturity_class"),
            "cesp_synthesis_throughput_gate_id": GP085_SYN03_GATE_ID_V1,
            "synthesis_throughput_targets": dict(throughput.get("throughput_targets") or {}),
        }
    )
    out["metrics"] = metrics

    omission_classes = dict(out.get("omission_classes") or {})
    targets = dict(throughput.get("throughput_targets") or {})
    eligible = int(tm.get("eligible_scopes") or 0)
    if eligible > 0 and not targets.get("scope_coverage_meets_target"):
        omission_classes[SYNTHESIS_STAGE_OMISSION_THROUGHPUT_GAP_V1] = 1
    if eligible > 0 and not targets.get("audit_empty_rate_within_limit"):
        omission_classes[SYNTHESIS_STAGE_OMISSION_ACTIVATION_AUDIT_EMPTY_V1] = 1
    out["omission_classes"] = omission_classes

    tp_state = str(throughput.get("substrate_state") or "healthy")
    stage_state = str(out.get("substrate_state") or "healthy")
    if tp_state == "degraded" and stage_state == "healthy":
        out["substrate_state"] = "degraded"
        drift = list(out.get("drift_warnings") or [])
        drift.append(f"{GP085_SYN03_GATE_ID_V1}: throughput_targets_not_met")
        out["drift_warnings"] = drift

    return _refresh_stage_envelope_receipt_digest_v1(out)


def project_synthesis_completeness_with_throughput_maturity_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Full synthesis stage: idle classification + throughput maturity."""
    from vector.domains.cortex.synthesis.synthesis_idle_classification import (
        project_synthesis_completeness_with_idle_classification_v1,
    )

    stage = project_synthesis_completeness_with_idle_classification_v1(
        session,
        tenant_id=tenant_id,
    )
    throughput = compute_synthesis_throughput_metrics_v1(session, tenant_id=tenant_id)
    return apply_synthesis_throughput_maturity_to_stage_v1(stage, throughput=throughput)
