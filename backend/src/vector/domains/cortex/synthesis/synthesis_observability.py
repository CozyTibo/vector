"""Phase 08 P08-21 — synthesis observability + runtime health model.

Normative: ``DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md`` §Observability.
**SYN-OBS-01** integer metrics + structured job logs; **SYN-OBS-02** S-LEG health predicates;
**SYN-OBS-03** operator alert thresholds from policy pack.
"""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
    SD_LLM_SCHEMA_V1,
    SD_PUBLISH_BLOCKED_V1,
    SD_REPLAY_DRIFT_V1,
    build_synthesis_omission_histogram_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    build_synthesis_coverage_catalog_v1,
    project_synthesis_completeness_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import synthesis_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
    SYNTHESIS_LEGALITY_PREDICATES_V1,
    evaluate_synthesis_s_leg_predicates_v1,
)
from vector.domains.cortex.synthesis.synthesis_query_plan import load_synthesis_policy_pack_v1
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    get_synthesis_replay_divergence_total_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

PHASE08_SYNTHESIS_OBSERVABILITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_OBS01_GATE_ID_V1: Final[str] = "G-P08-OBS-01"

SYNTHESIS_OBSERVABILITY_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md"
)

SYNTHESIS_OBS_ENGINE_BUILD_REF_V1: Final[str] = "syn-orchestrator-v1-stub"

SYN_OBS01_RULE_ID_V1: Final[str] = "SYN-OBS-01"

SYN_OBS02_RULE_ID_V1: Final[str] = "SYN-OBS-02"

SYN_OBS03_RULE_ID_V1: Final[str] = "SYN-OBS-03"

_DEFAULT_OBSERVABILITY_THRESHOLDS_V1: Final[dict[str, int]] = {
    "completeness_critical_percent": 50,
    "job_failure_rate_percent": 10,
    "max_publication_lag_epochs": 1,
    "sd_critical_spike_per_hour": 3,
    "replay_divergence_spike_per_hour": 3,
}

_DEGRADED_LEGALITY_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "synthesis_degraded",
        "synthesis_partial",
        "synthesis_unverifiable",
        "synthesis_forbidden",
    }
)

_CRITICAL_SD_CODES_V1: Final[frozenset[str]] = frozenset(
    {SD_PUBLISH_BLOCKED_V1, SD_LLM_SCHEMA_V1, SD_REPLAY_DRIFT_V1}
)

_SYNTHESIS_JOBS_TOTAL_V1: int = 0
_SYNTHESIS_JOB_FAILURES_TOTAL_V1: int = 0
_SYNTHESIS_JOBS_BY_LEGALITY_V1: dict[str, int] = defaultdict(int)
_SYNTHESIS_JOBS_BY_WORKLOAD_V1: dict[str, int] = defaultdict(int)
_SYNTHESIS_SD_CODES_V1: dict[str, int] = defaultdict(int)
_SYNTHESIS_LLM_TOKENS_BY_ROUTE_V1: dict[str, int] = defaultdict(int)
_SYNTHESIS_JOB_DURATION_MS_SAMPLES_V1: deque[int] = deque(maxlen=512)
_SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1: int = 0
_LAST_REPLAY_DIVERGENCE_AT_V1: str | None = None
_TENANT_RECENT_JOB_ROLLUP_V1: dict[str, deque[dict[str, Any]]] = defaultdict(
    lambda: deque(maxlen=100)
)


class SynthesisObservabilityError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def policy_pack_observability_thresholds_v1(
    pack: Mapping[str, Any] | None = None,
) -> dict[str, int]:
    body = dict(pack or load_synthesis_policy_pack_v1())
    raw = body.get("observability")
    if not isinstance(raw, dict):
        return dict(_DEFAULT_OBSERVABILITY_THRESHOLDS_V1)
    out = dict(_DEFAULT_OBSERVABILITY_THRESHOLDS_V1)
    for key in _DEFAULT_OBSERVABILITY_THRESHOLDS_V1:
        if key in raw:
            out[key] = int(raw[key])
    return out


def get_synthesis_jobs_total_v1() -> int:
    return _SYNTHESIS_JOBS_TOTAL_V1


def get_synthesis_job_failures_total_v1() -> int:
    return _SYNTHESIS_JOB_FAILURES_TOTAL_V1


def get_synthesis_jobs_by_legality_v1() -> dict[str, int]:
    return dict(_SYNTHESIS_JOBS_BY_LEGALITY_V1)


def get_synthesis_jobs_by_workload_v1() -> dict[str, int]:
    return dict(_SYNTHESIS_JOBS_BY_WORKLOAD_V1)


def get_synthesis_publication_lag_epochs_gauge_v1() -> int:
    return _SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1


def record_synthesis_publication_lag_v1(lag_epochs: int) -> None:
    """Update in-process publication lag gauge after epoch bump."""
    global _SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1
    _SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1 = max(_SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1, max(0, int(lag_epochs)))


def get_last_synthesis_replay_divergence_at_v1() -> str | None:
    return _LAST_REPLAY_DIVERGENCE_AT_V1


def reset_synthesis_observability_metrics_v1() -> None:
    """Test isolation — clear in-process counters."""
    global _SYNTHESIS_JOBS_TOTAL_V1, _SYNTHESIS_JOB_FAILURES_TOTAL_V1, _SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1
    global _LAST_REPLAY_DIVERGENCE_AT_V1
    _SYNTHESIS_JOBS_TOTAL_V1 = 0
    _SYNTHESIS_JOB_FAILURES_TOTAL_V1 = 0
    _SYNTHESIS_JOBS_BY_LEGALITY_V1.clear()
    _SYNTHESIS_JOBS_BY_WORKLOAD_V1.clear()
    _SYNTHESIS_SD_CODES_V1.clear()
    _SYNTHESIS_LLM_TOKENS_BY_ROUTE_V1.clear()
    _SYNTHESIS_JOB_DURATION_MS_SAMPLES_V1.clear()
    _SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1 = 0
    _LAST_REPLAY_DIVERGENCE_AT_V1 = None
    _TENANT_RECENT_JOB_ROLLUP_V1.clear()


def _percentile_int(samples: Sequence[int], pct: float) -> int:
    if not samples:
        return 0
    ordered = sorted(int(s) for s in samples)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def snapshot_synthesis_metrics_v1() -> dict[str, Any]:
    """Control-plane metrics snapshot (integers / millis only)."""
    return {
        "synthesis_jobs_total": get_synthesis_jobs_total_v1(),
        "synthesis_jobs_by_legality": get_synthesis_jobs_by_legality_v1(),
        "synthesis_jobs_by_workload": get_synthesis_jobs_by_workload_v1(),
        "synthesis_job_failures_total": get_synthesis_job_failures_total_v1(),
        "synthesis_job_duration_ms_p50": _percentile_int(_SYNTHESIS_JOB_DURATION_MS_SAMPLES_V1, 50),
        "synthesis_job_duration_ms_p95": _percentile_int(_SYNTHESIS_JOB_DURATION_MS_SAMPLES_V1, 95),
        "synthesis_llm_tokens_by_route": dict(_SYNTHESIS_LLM_TOKENS_BY_ROUTE_V1),
        "synthesis_sd_codes": dict(_SYNTHESIS_SD_CODES_V1),
        "synthesis_sd_codes_histogram": build_synthesis_omission_histogram_v1(),
        "synthesis_publication_lag_epochs": get_synthesis_publication_lag_epochs_gauge_v1(),
        "synthesis_replay_divergence_total": get_synthesis_replay_divergence_total_v1(),
    }


def record_synthesis_legality_failure_v1(*, reason: str) -> None:
    global _SYNTHESIS_JOB_FAILURES_TOTAL_V1
    _SYNTHESIS_JOB_FAILURES_TOTAL_V1 += 1
    _SYNTHESIS_SD_CODES_V1[f"legality_failure:{reason}"] += 1


def _record_sd_rows_v1(rows: Sequence[Mapping[str, Any]]) -> None:
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        sd = str(row.get("sd_code") or row.get("synthesis_omission_class") or "").strip()
        if not sd:
            continue
        count = int(row.get("trigger_count", 1))
        _SYNTHESIS_SD_CODES_V1[sd] += max(count, 1)


def _record_llm_invocations_v1(invocations: Sequence[Mapping[str, Any]]) -> None:
    for inv in invocations:
        if not isinstance(inv, Mapping):
            continue
        route_id = str(inv.get("model_route_id") or "unknown")
        tokens = int(inv.get("tokens_used") or 0)
        if tokens > 0:
            _SYNTHESIS_LLM_TOKENS_BY_ROUTE_V1[route_id] += tokens


def build_synthesis_job_log_v1(
    *,
    envelope: Mapping[str, Any],
    job_id: str,
    status: str,
    synthesis_legality_class: str,
    duration_ms: int,
    synthesis_job_replay_identity: str = "",
    receipt_digest: str = "",
    omission_count: int = 0,
    artifact_id: str | None = None,
    engine_build_ref: str = SYNTHESIS_OBS_ENGINE_BUILD_REF_V1,
    policy_digest: str | None = None,
) -> dict[str, Any]:
    """Structured execution log — digests and counts only (**SYN-OBS-01**)."""
    return {
        "event": "synthesis_job_completed",
        "job_id": job_id,
        "status": status,
        "synthesis_job_replay_identity": synthesis_job_replay_identity,
        "synthesis_workload_class": str(envelope.get("synthesis_workload_class") or ""),
        "synthesis_intent": str(envelope.get("synthesis_intent") or ""),
        "execution_partition": str(envelope.get("execution_partition") or "authoritative"),
        "synthesis_legality_class": synthesis_legality_class,
        "omission_count": max(0, int(omission_count)),
        "duration_ms": max(0, int(duration_ms)),
        "artifact_id": artifact_id,
        "engine_build_ref": engine_build_ref,
        "policy_digest": policy_digest or synthesis_policy_pack_digest_v1(),
        "receipt_digest": receipt_digest,
    }


def _rollup_recent_jobs_v1(tenant_id: uuid.UUID | str) -> dict[str, Any]:
    recent = list(_TENANT_RECENT_JOB_ROLLUP_V1.get(str(tenant_id), ()))
    if not recent:
        return {"sample_count": 0, "degraded_percent": 0, "failure_percent": 0, "by_legality": {}}
    degraded = sum(
        1 for r in recent if str(r.get("synthesis_legality_class")) in _DEGRADED_LEGALITY_CLASSES_V1
    )
    failed = sum(1 for r in recent if str(r.get("status")) == "failed")
    by_leg: dict[str, int] = defaultdict(int)
    for r in recent:
        by_leg[str(r.get("synthesis_legality_class") or "unknown")] += 1
    n = len(recent)
    return {
        "sample_count": n,
        "degraded_percent": int(round(100.0 * degraded / n)),
        "failure_percent": int(round(100.0 * failed / n)),
        "by_legality": dict(by_leg),
    }


def build_s_leg_health_predicates_v1(
    *,
    upstream_retrieval_legality: str = "retrieval_replay_safe",
    synthesis_intent: str = "inspect",
    execution_partition: str = "authoritative",
) -> dict[str, Any]:
    """S-LEG predicate snapshot for health strip (**SYN-OBS-02**)."""
    evaluated = evaluate_synthesis_s_leg_predicates_v1(
        upstream_retrieval_legality=upstream_retrieval_legality,
        synthesis_intent=synthesis_intent,
        execution_partition=execution_partition,
        synthesis_omission_rows=[],
        hit_evidence_legalities=None,
        llm_schema_failed=False,
    )
    predicates: list[dict[str, Any]] = []
    for pred in SYNTHESIS_LEGALITY_PREDICATES_V1:
        pid = pred.predicate_id
        ok = bool(evaluated.get(pid))
        predicates.append(
            {
                "predicate_id": pid,
                "ok": ok,
                "failure_class": None if ok else pred.failure_class,
            }
        )
    return {
        "predicates": predicates,
        "all_passed": all(p["ok"] for p in predicates),
    }


def _count_tenant_jobs_v1(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    total = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(CortexSynthesisJob.tenant_id == tenant_id)
        )
        or 0
    )
    failed = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status == "failed",
            )
        )
        or 0
    )
    return {"total": total, "failed": failed}


def _count_recent_critical_sd_artifacts_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    window_hours: int = 1,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    rows = session.scalars(
        select(CortexSynthesisArtifact).where(
            CortexSynthesisArtifact.tenant_id == tenant_id,
            CortexSynthesisArtifact.created_at >= cutoff,
        )
    ).all()
    critical = 0
    for row in rows:
        body = row.body_json or {}
        rollup = body.get("synthesis_degradation_rollup")
        if not isinstance(rollup, Mapping):
            continue
        hist = rollup.get("omission_histogram")
        if not isinstance(hist, Mapping):
            continue
        for sd in _CRITICAL_SD_CODES_V1:
            if int(hist.get(sd) or 0) > 0:
                critical += 1
                break
    return critical


def evaluate_synthesis_alerts_v1(
    *,
    health: Mapping[str, Any],
    metrics: Mapping[str, Any],
    thresholds: Mapping[str, int],
    tenant_jobs_present: int,
) -> list[dict[str, Any]]:
    """Operator-facing alert evaluation (**SYN-OBS-03**)."""
    alerts: list[dict[str, Any]] = []
    completeness = int(health.get("synthesis_completeness_percent") or 0)
    crit_pct = int(thresholds.get("completeness_critical_percent", 50))
    if tenant_jobs_present > 0 and completeness < crit_pct:
        alerts.append(
            {
                "alert_id": "synthesis_coverage_critical",
                "severity": "critical",
                "message": (
                    f"Synthesis coverage {completeness}% below {crit_pct}% with jobs present"
                ),
            }
        )
    sd_critical = int(health.get("sd_critical_count") or 0)
    sd_spike = int(thresholds.get("sd_critical_spike_per_hour", 3))
    recent_sd = int(health.get("recent_critical_sd_artifacts_1h") or 0)
    if recent_sd > sd_spike:
        alerts.append(
            {
                "alert_id": "sd_critical_spike",
                "severity": "critical",
                "message": f">{sd_spike} artifacts with critical SD-* in the last hour ({recent_sd})",
            }
        )
    elif sd_critical > 0:
        alerts.append(
            {
                "alert_id": "sd_critical_present",
                "severity": "warning",
                "message": f"tenant sd_critical_count={sd_critical}",
            }
        )
    max_lag = int(thresholds.get("max_publication_lag_epochs", 1))
    lag_epochs = int(health.get("publication_lag_epochs") or 0)
    if lag_epochs > max_lag:
        alerts.append(
            {
                "alert_id": "publication_lag",
                "severity": "warning",
                "message": f"publication_lag_epochs={lag_epochs} exceeds policy max {max_lag}",
            }
        )
    fail_rate_limit = int(thresholds.get("job_failure_rate_percent", 10))
    failure_pct = int(health.get("tenant_job_failure_percent") or 0)
    if failure_pct > fail_rate_limit:
        alerts.append(
            {
                "alert_id": "job_failure_burst",
                "severity": "warning",
                "message": f"synthesis job failure rate {failure_pct}% exceeds {fail_rate_limit}%",
            }
        )
    div_spike = int(thresholds.get("replay_divergence_spike_per_hour", 3))
    if int(metrics.get("synthesis_replay_divergence_total") or 0) > div_spike:
        alerts.append(
            {
                "alert_id": "replay_divergence_elevated",
                "severity": "warning",
                "message": "synthesis replay divergence counter elevated",
            }
        )
    substrate_health = str(health.get("substrate_health_state") or "")
    if substrate_health in ("critical", "replay_conflicted"):
        alerts.append(
            {
                "alert_id": "substrate_health_critical",
                "severity": "critical",
                "message": f"substrate_health_state={substrate_health}",
            }
        )
    return alerts


def build_synthesis_runtime_health_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Runtime health model for admin health strip."""
    coverage = build_synthesis_coverage_catalog_v1(session, tenant_id=tenant_id)
    stage = project_synthesis_completeness_v1(session, tenant_id=tenant_id)
    metrics_stage = dict(stage.get("metrics") or {})
    rollup = _rollup_recent_jobs_v1(tenant_id)
    lag = int(metrics_stage.get("lag_epochs") or metrics_stage.get("lag_vs_retrieval") or 0)
    global _SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1
    _SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1 = max(_SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1, lag)
    job_counts = _count_tenant_jobs_v1(session, tenant_id=tenant_id)
    failure_pct = 0
    if job_counts["total"] > 0:
        failure_pct = int(round(100.0 * job_counts["failed"] / job_counts["total"]))
    recent_critical_sd = _count_recent_critical_sd_artifacts_v1(session, tenant_id=tenant_id)
    s_leg = build_s_leg_health_predicates_v1()
    thresholds = policy_pack_observability_thresholds_v1()
    metric_snap = snapshot_synthesis_metrics_v1()
    health_body: dict[str, Any] = {
        "schema_version": PHASE08_SYNTHESIS_OBSERVABILITY_RUNTIME_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "substrate_state": coverage.get("substrate_state"),
        "substrate_health_state": coverage.get("status"),
        "replay_posture": coverage.get("replay_posture"),
        "publication_epoch": coverage.get("publication_epoch"),
        "published_index_epoch": metrics_stage.get("published_index_epoch"),
        "publication_lag_epochs": lag,
        "synthesis_completeness_percent": int(coverage.get("coverage_percent") or 0),
        "sd_critical_count": int(coverage.get("sd_critical_count") or 0),
        "degraded_percent": rollup["degraded_percent"],
        "tenant_job_failure_percent": failure_pct,
        "tenant_jobs_total": job_counts["total"],
        "tenant_jobs_failed": job_counts["failed"],
        "recent_job_rollup": rollup,
        "recent_critical_sd_artifacts_1h": recent_critical_sd,
        "last_replay_divergence_at": get_last_synthesis_replay_divergence_at_v1(),
        "s_leg_health": s_leg,
        "metrics": metric_snap,
        "observability_thresholds": thresholds,
        "engine_build_ref": SYNTHESIS_OBS_ENGINE_BUILD_REF_V1,
        "policy_digest": synthesis_policy_pack_digest_v1(),
    }
    health_body["active_alerts"] = evaluate_synthesis_alerts_v1(
        health=health_body,
        metrics=metric_snap,
        thresholds=thresholds,
        tenant_jobs_present=job_counts["total"],
    )
    return health_body


def build_synthesis_health_strip_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Compact admin health strip payload."""
    health = build_synthesis_runtime_health_v1(session, tenant_id=tenant_id)
    return {
        "substrate_state": health.get("substrate_state"),
        "substrate_health_state": health.get("substrate_health_state"),
        "replay_posture": health.get("replay_posture"),
        "publication_epoch": health.get("publication_epoch"),
        "synthesis_completeness_percent": health.get("synthesis_completeness_percent"),
        "publication_lag_epochs": health.get("publication_lag_epochs"),
        "sd_critical_count": health.get("sd_critical_count"),
        "tenant_job_failure_percent": health.get("tenant_job_failure_percent"),
        "last_replay_divergence_at": health.get("last_replay_divergence_at"),
        "active_alerts": health.get("active_alerts") or [],
        "s_leg_all_passed": (health.get("s_leg_health") or {}).get("all_passed"),
    }


def build_synthesis_observability_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_observability_v1",
        "synthesis_observability_runtime_schema_version": (
            PHASE08_SYNTHESIS_OBSERVABILITY_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_OBS01_GATE_ID_V1,
        "spec_ref": SYNTHESIS_OBSERVABILITY_SPEC_REF_V1,
        "rules": [
            {"id": SYN_OBS01_RULE_ID_V1, "text": "Integer metrics + structured job logs"},
            {"id": SYN_OBS02_RULE_ID_V1, "text": "S-LEG health predicates on health strip"},
            {"id": SYN_OBS03_RULE_ID_V1, "text": "Policy-pack alert thresholds"},
        ],
        "metric_names": [
            "synthesis_jobs_total",
            "synthesis_jobs_by_legality",
            "synthesis_jobs_by_workload",
            "synthesis_job_failures_total",
            "synthesis_job_duration_ms_p50",
            "synthesis_job_duration_ms_p95",
            "synthesis_llm_tokens_by_route",
            "synthesis_sd_codes",
            "synthesis_publication_lag_epochs",
            "synthesis_replay_divergence_total",
        ],
        "default_thresholds": dict(_DEFAULT_OBSERVABILITY_THRESHOLDS_V1),
        "engine_build_ref": SYNTHESIS_OBS_ENGINE_BUILD_REF_V1,
    }


def record_synthesis_job_observability_v1(
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    envelope: Mapping[str, Any],
    status: str,
    synthesis_legality_class: str,
    duration_ms: int,
    synthesis_job_replay_identity: str = "",
    receipt_digest: str = "",
    synthesis_omission_rows: Sequence[Mapping[str, Any]] | None = None,
    llm_invocations: Sequence[Mapping[str, Any]] | None = None,
    artifact_id: str | None = None,
    replay_twin_passed: bool | None = None,
    publication_lag_epochs: int | None = None,
) -> dict[str, Any]:
    """Record metrics and structured log for one completed synthesis job."""
    global _SYNTHESIS_JOBS_TOTAL_V1, _SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1
    _SYNTHESIS_JOBS_TOTAL_V1 += 1
    if status == "failed":
        global _SYNTHESIS_JOB_FAILURES_TOTAL_V1
        _SYNTHESIS_JOB_FAILURES_TOTAL_V1 += 1
    legality = str(synthesis_legality_class or "synthesis_partial")
    workload = str(envelope.get("synthesis_workload_class") or "unknown")
    _SYNTHESIS_JOBS_BY_LEGALITY_V1[legality] += 1
    _SYNTHESIS_JOBS_BY_WORKLOAD_V1[workload] += 1
    omissions = list(synthesis_omission_rows or [])
    _record_sd_rows_v1(omissions)
    _record_llm_invocations_v1(llm_invocations or [])
    _SYNTHESIS_JOB_DURATION_MS_SAMPLES_V1.append(max(0, int(duration_ms)))
    if publication_lag_epochs is not None:
        _SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1 = max(
            _SYNTHESIS_PUBLICATION_LAG_EPOCHS_V1,
            int(publication_lag_epochs),
        )
    if replay_twin_passed is False:
        global _LAST_REPLAY_DIVERGENCE_AT_V1
        _LAST_REPLAY_DIVERGENCE_AT_V1 = datetime.now(timezone.utc).isoformat()
    _TENANT_RECENT_JOB_ROLLUP_V1[str(tenant_id)].append(
        {
            "status": status,
            "synthesis_legality_class": legality,
            "synthesis_workload_class": workload,
        }
    )
    log_row = build_synthesis_job_log_v1(
        envelope=envelope,
        job_id=str(job_id),
        status=status,
        synthesis_legality_class=legality,
        duration_ms=duration_ms,
        synthesis_job_replay_identity=synthesis_job_replay_identity,
        receipt_digest=receipt_digest,
        omission_count=len(omissions),
        artifact_id=artifact_id,
    )
    return {
        "job_log": log_row,
        "metrics": snapshot_synthesis_metrics_v1(),
    }


def _obs_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_OBS01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase08_synthesis_observability_runtime_schema_version": (
                PHASE08_SYNTHESIS_OBSERVABILITY_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp08_obs01_metrics_and_health_static() -> dict[str, Any]:
    """**G-P08-OBS-01** — integer metrics, health fields, job log law."""
    errors: list[str] = []
    metrics = snapshot_synthesis_metrics_v1()
    for key in (
        "synthesis_jobs_total",
        "synthesis_job_failures_total",
        "synthesis_job_duration_ms_p50",
        "synthesis_job_duration_ms_p95",
        "synthesis_publication_lag_epochs",
    ):
        if not isinstance(metrics.get(key), int):
            errors.append(f"metric_not_int:{key}")
    log = build_synthesis_job_log_v1(
        envelope={
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
        },
        job_id="job-test",
        status="completed",
        synthesis_legality_class="synthesis_replay_safe",
        duration_ms=42,
        synthesis_job_replay_identity="sha256:" + "a" * 64,
        receipt_digest="sha256:" + "b" * 64,
        omission_count=1,
    )
    for field in (
        "job_id",
        "synthesis_workload_class",
        "duration_ms",
        "engine_build_ref",
        "policy_digest",
        "synthesis_legality_class",
    ):
        if field not in log:
            errors.append(f"log_missing:{field}")
    if "claims" in log:
        errors.append("log_must_not_embed_claims")
    s_leg = build_s_leg_health_predicates_v1()
    if not s_leg.get("predicates"):
        errors.append("s_leg_predicates_empty")
    thresholds = policy_pack_observability_thresholds_v1()
    alerts = evaluate_synthesis_alerts_v1(
        health={
            "synthesis_completeness_percent": 20,
            "publication_lag_epochs": 3,
            "sd_critical_count": 2,
            "substrate_health_state": "critical",
            "recent_critical_sd_artifacts_1h": 5,
            "tenant_job_failure_percent": 25,
        },
        metrics={"synthesis_replay_divergence_total": 10},
        thresholds=thresholds,
        tenant_jobs_present=3,
    )
    if not alerts:
        errors.append("expected_alerts")
    cat = build_synthesis_observability_catalog_v1()
    if cat["gate_id"] != GP08_OBS01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    return _obs_meta("gp08_obs01_metrics_and_health", errors)
