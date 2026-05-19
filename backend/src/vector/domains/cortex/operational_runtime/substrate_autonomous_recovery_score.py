"""Phase 08.5 P085-29 — autonomous recovery score (**G-P085-HEALTH-02**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-operational-health-maturity-doctrine.md``.
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.recovery_receipts import (
    RECOVERY_RECEIPT_OUTCOME_RECOVERED,
    list_recovery_receipts_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_STALLED,
    list_stale_waiting_continuations_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_dead_letter import (
    DLQ_STATUS_OPEN,
)
from vector.infrastructure.db.models.cortex_pipeline_continuation import (
    CortexPipelineContinuationState,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_dead_letter import (
    CortexSubstratePipelineDeadLetter,
)

PHASE085_AUTONOMOUS_RECOVERY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_AUTONOMOUS_RECOVERY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-operational-health-maturity-doctrine.md"
)

GP085_HEALTH02_GATE_ID_V1: Final[str] = "G-P085-HEALTH-02"

METRIC_RECOVERY_SCORE_V1: Final[str] = "recovery_score"
METRIC_RECOVERED_WATCHDOG_V1: Final[str] = "recovered_watchdog"
METRIC_RECOVERED_TOTAL_V1: Final[str] = "recovered_total"
METRIC_FAILED_DLQ_V1: Final[str] = "failed_dlq"

HEALTH_DIM_AUTONOMOUS_RECOVERY_V1: Final[str] = "autonomous_recovery_health"

_RECOVERY_HEALTH_BAND_HEALTHY_V1: Final[str] = "healthy"
_RECOVERY_HEALTH_BAND_DEGRADED_V1: Final[str] = "degraded"
_RECOVERY_HEALTH_BAND_CRITICAL_V1: Final[str] = "critical"

_DEFAULT_RECOVERY_WINDOW_DAYS_V1: Final[int] = 7
_DEFAULT_RECOVERY_SCORE_TARGET_V1: Final[float] = 0.9
_DEFAULT_RECOVERY_DEGRADED_FLOOR_V1: Final[float] = 0.7


def get_autonomous_recovery_thresholds_v1() -> dict[str, Any]:
    try:
        from vector.settings import get_settings

        cfg = get_settings()
        return {
            "window_days": int(cfg.cortex_autonomous_recovery_score_window_days),
            "score_target": float(cfg.cortex_autonomous_recovery_score_target),
            "degraded_floor": float(cfg.cortex_autonomous_recovery_score_degraded_floor),
            "stability_stall_window_hours": int(
                cfg.cortex_autonomous_recovery_stability_stall_window_hours
            ),
        }
    except Exception:  # noqa: BLE001
        return {
            "window_days": _DEFAULT_RECOVERY_WINDOW_DAYS_V1,
            "score_target": _DEFAULT_RECOVERY_SCORE_TARGET_V1,
            "degraded_floor": _DEFAULT_RECOVERY_DEGRADED_FLOOR_V1,
            "stability_stall_window_hours": 24,
        }


def _parse_recorded_at_v1(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return None


def _receipt_in_window_v1(receipt: Mapping[str, Any], *, since: datetime) -> bool:
    recorded = _parse_recorded_at_v1(str(receipt.get("recorded_at") or "") or None)
    if recorded is None:
        return True
    return recorded >= since


def collect_recovery_receipt_counts_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    since: datetime,
) -> dict[str, int]:
    """Count recovery receipts for tenant since ``since``."""
    recovered_watchdog = 0
    recovered_total = 0
    failed_watchdog = 0

    continuations = list(
        session.scalars(
            select(CortexPipelineContinuationState).where(
                CortexPipelineContinuationState.tenant_id == tenant_id,
                CortexPipelineContinuationState.updated_at >= since,
            )
        ).all()
    )
    for continuation in continuations:
        for receipt in list_recovery_receipts_v1(continuation):
            if not _receipt_in_window_v1(receipt, since=since):
                continue
            outcome = str(receipt.get("outcome") or "")
            operator_action = str(receipt.get("operator_action") or "")
            is_watchdog = operator_action == "auto"
            if outcome == RECOVERY_RECEIPT_OUTCOME_RECOVERED:
                recovered_total += 1
                if is_watchdog:
                    recovered_watchdog += 1
            elif is_watchdog and outcome == "failed":
                failed_watchdog += 1

    return {
        METRIC_RECOVERED_WATCHDOG_V1: recovered_watchdog,
        METRIC_RECOVERED_TOTAL_V1: recovered_total,
        "failed_watchdog_attempts": failed_watchdog,
    }


def count_failed_dlq_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    since: datetime,
) -> int:
    """Open DLQ rows created in the rolling window (**failed_dlq**)."""
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexSubstratePipelineDeadLetter)
            .where(
                CortexSubstratePipelineDeadLetter.tenant_id == tenant_id,
                CortexSubstratePipelineDeadLetter.dlq_status == DLQ_STATUS_OPEN,
                CortexSubstratePipelineDeadLetter.created_at >= since,
            )
        )
        or 0
    )


def compute_autonomous_recovery_score_v1(
    *,
    recovered_watchdog: int,
    recovered_total: int,
    failed_dlq: int,
) -> float:
    """``recovery_score = recovered_watchdog / (recovered + failed_dlq)``; idle → 1.0."""
    denom = int(recovered_total) + int(failed_dlq)
    if denom <= 0:
        return 1.0
    return round(float(recovered_watchdog) / float(denom), 4)


def evaluate_autonomous_recovery_health_v1(
    *,
    recovery_score: float,
    score_target: float,
    degraded_floor: float,
) -> dict[str, Any]:
    if float(recovery_score) >= float(score_target):
        band = _RECOVERY_HEALTH_BAND_HEALTHY_V1
        reason = "recovery_score_meets_target"
    elif float(recovery_score) >= float(degraded_floor):
        band = _RECOVERY_HEALTH_BAND_DEGRADED_V1
        reason = "recovery_score_below_target"
    else:
        band = _RECOVERY_HEALTH_BAND_CRITICAL_V1
        reason = "recovery_score_critical"
    return {
        "band": band,
        "reason": reason,
        METRIC_RECOVERY_SCORE_V1: recovery_score,
        "score_target": score_target,
        "degraded_floor": degraded_floor,
        "meets_target": float(recovery_score) >= float(score_target),
    }


def count_stall_events_in_window_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_window_hours: int,
    stall_threshold_seconds: int = 1800,
) -> int:
    """Stalled continuations currently or stale-waiting within stability window."""
    since = datetime.now(tz=UTC) - timedelta(hours=max(1, int(stall_window_hours)))
    stalled_status = int(
        session.scalar(
            select(func.count())
            .select_from(CortexPipelineContinuationState)
            .where(
                CortexPipelineContinuationState.tenant_id == tenant_id,
                CortexPipelineContinuationState.continuation_status == CONTINUATION_STATUS_STALLED,
                CortexPipelineContinuationState.updated_at >= since,
            )
        )
        or 0
    )
    stale_waiting = len(
        list_stale_waiting_continuations_v1(
            session,
            tenant_id=tenant_id,
            stall_threshold_seconds=stall_threshold_seconds,
            limit=50,
        )
    )
    return stalled_status + stale_waiting


def evaluate_tenant_operational_stability_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    recovery_score: float,
    score_target: float,
    stall_window_hours: int,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """**Stable** = no stall events in window + ``recovery_score`` ≥ target."""
    stall_events = count_stall_events_in_window_v1(
        session,
        tenant_id=tenant_id,
        stall_window_hours=stall_window_hours,
        stall_threshold_seconds=stall_threshold_seconds,
    )
    no_stalls = stall_events == 0
    score_ok = float(recovery_score) >= float(score_target)
    return {
        "stable": no_stalls and score_ok,
        "no_stall_events": no_stalls,
        "recovery_score_meets_target": score_ok,
        "stall_events_in_window": stall_events,
        "stall_window_hours": stall_window_hours,
    }


def evaluate_autonomous_recovery_score_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Full **G-P085-HEALTH-02** tenant recovery score evaluation."""
    thresholds = get_autonomous_recovery_thresholds_v1()
    window_days = int(thresholds["window_days"])
    since = datetime.now(tz=UTC) - timedelta(days=max(1, window_days))

    receipt_counts = collect_recovery_receipt_counts_v1(
        session,
        tenant_id=tenant_id,
        since=since,
    )
    failed_dlq = count_failed_dlq_v1(session, tenant_id=tenant_id, since=since)
    recovered_watchdog = int(receipt_counts[METRIC_RECOVERED_WATCHDOG_V1])
    recovered_total = int(receipt_counts[METRIC_RECOVERED_TOTAL_V1])

    recovery_score = compute_autonomous_recovery_score_v1(
        recovered_watchdog=recovered_watchdog,
        recovered_total=recovered_total,
        failed_dlq=failed_dlq,
    )
    health_detail = evaluate_autonomous_recovery_health_v1(
        recovery_score=recovery_score,
        score_target=float(thresholds["score_target"]),
        degraded_floor=float(thresholds["degraded_floor"]),
    )
    stability = evaluate_tenant_operational_stability_v1(
        session,
        tenant_id=tenant_id,
        recovery_score=recovery_score,
        score_target=float(thresholds["score_target"]),
        stall_window_hours=int(thresholds["stability_stall_window_hours"]),
        stall_threshold_seconds=stall_threshold_seconds,
    )

    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_HEALTH02_GATE_ID_V1,
        "window_days": window_days,
        "window_started_at": since.isoformat(),
        "metrics": {
            METRIC_RECOVERY_SCORE_V1: recovery_score,
            METRIC_RECOVERED_WATCHDOG_V1: recovered_watchdog,
            METRIC_RECOVERED_TOTAL_V1: recovered_total,
            METRIC_FAILED_DLQ_V1: failed_dlq,
            "failed_watchdog_attempts": int(receipt_counts.get("failed_watchdog_attempts") or 0),
        },
        "formula": "recovered_watchdog / (recovered + failed_dlq)",
        "thresholds": thresholds,
        "autonomous_recovery_health": health_detail,
        "operational_stability": stability,
        "autonomous_recovery_health_band": health_detail["band"],
    }


def build_autonomous_recovery_card_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Operator autonomous recovery dashboard card."""
    eval_out = evaluate_autonomous_recovery_score_v1(
        session,
        tenant_id=tenant_id,
        stall_threshold_seconds=stall_threshold_seconds,
    )
    metrics = dict(eval_out.get("metrics") or {})
    return {
        "surface_kind": "autonomous_recovery_card",
        "gate_id": GP085_HEALTH02_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        METRIC_RECOVERY_SCORE_V1: metrics.get(METRIC_RECOVERY_SCORE_V1),
        "metrics": metrics,
        "autonomous_recovery_health": eval_out.get("autonomous_recovery_health"),
        "operational_stability": eval_out.get("operational_stability"),
        "formula": eval_out.get("formula"),
        "detail_route": (
            f"/admin/tenants/{tenant_id}/cortex/operational-runtime/autonomous-recovery"
        ),
    }


def build_substrate_autonomous_recovery_catalog_v1() -> dict[str, Any]:
    thresholds = get_autonomous_recovery_thresholds_v1()
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_autonomous_recovery_runtime_schema_version": int(
            PHASE085_AUTONOMOUS_RECOVERY_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_AUTONOMOUS_RECOVERY_SPEC_REF_V1,
        "primary_gate_id": GP085_HEALTH02_GATE_ID_V1,
        "metric_ids": [
            METRIC_RECOVERY_SCORE_V1,
            METRIC_RECOVERED_WATCHDOG_V1,
            METRIC_RECOVERED_TOTAL_V1,
            METRIC_FAILED_DLQ_V1,
        ],
        "formula": "recovered_watchdog / (recovered + failed_dlq)",
        "score_target": thresholds["score_target"],
        "window_days": thresholds["window_days"],
        "health_dimension_id": HEALTH_DIM_AUTONOMOUS_RECOVERY_V1,
        "stability_definition": "no_stall_events + recovery_score >= target",
        "evaluation_entrypoint": "evaluate_autonomous_recovery_score_v1",
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_autonomous_recovery_score"
        ),
    }


def verify_gp085_health02_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_autonomous_recovery_catalog_v1()
    if cat["primary_gate_id"] != GP085_HEALTH02_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    if compute_autonomous_recovery_score_v1(
        recovered_watchdog=9,
        recovered_total=10,
        failed_dlq=0,
    ) != 0.9:
        errors.append("recovery_score_formula")

    if compute_autonomous_recovery_score_v1(
        recovered_watchdog=0,
        recovered_total=0,
        failed_dlq=0,
    ) != 1.0:
        errors.append("idle_tenant_score_should_be_one")

    health = evaluate_autonomous_recovery_health_v1(
        recovery_score=0.95,
        score_target=0.9,
        degraded_floor=0.7,
    )
    if health["band"] != _RECOVERY_HEALTH_BAND_HEALTHY_V1:
        errors.append("healthy_band_fixture")

    degraded = evaluate_autonomous_recovery_health_v1(
        recovery_score=0.75,
        score_target=0.9,
        degraded_floor=0.7,
    )
    if degraded["band"] != _RECOVERY_HEALTH_BAND_DEGRADED_V1:
        errors.append("degraded_band_fixture")

    critical = evaluate_autonomous_recovery_health_v1(
        recovery_score=0.5,
        score_target=0.9,
        degraded_floor=0.7,
    )
    if critical["band"] != _RECOVERY_HEALTH_BAND_CRITICAL_V1:
        errors.append("critical_band_fixture")

    from vector.domains.cortex.operational_runtime import (
        substrate_operational_health_dimensions as sod,
    )

    if "evaluate_autonomous_recovery_score_v1" not in inspect.getsource(
        sod.evaluate_operational_health_dimensions_v1
    ):
        errors.append("health_dimensions_missing_recovery_score")

    from vector.domains.cortex.substrate_pipeline import substrate_operational_health as soh

    if "autonomous_recovery" not in inspect.getsource(
        soh.evaluate_substrate_operational_health_v1
    ):
        errors.append("operational_health_missing_recovery_score")

    passed = not errors
    return {
        "id": GP085_HEALTH02_GATE_ID_V1,
        "name": "cesp_substrate_autonomous_recovery_score",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
