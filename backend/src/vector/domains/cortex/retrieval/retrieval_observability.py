"""Phase 07 P07-22 — retrieval observability + runtime health model.

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-observability-doctrine.md``.
**RET-OBS-01** integer metrics + structured query logs; **RET-OBS-02** R-LEG health predicates;
**RET-OBS-03** operator alert thresholds from policy pack.
"""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.retrieval_bounded_caps import (
    load_retrieval_policy_pack_v1,
    retrieval_policy_pack_digest_v1,
)
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    build_retrieval_coverage_catalog_v1,
    project_retrieval_completeness_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_matrix import (
    R_LEG_PREDICATE_FAILURE_CLASS_V1,
    list_retrieval_legality_predicate_ids_v1,
    run_retrieval_r_leg_precheck_v1,
)
from vector.domains.cortex.retrieval.retrieval_runtime_legality_matrix import (
    detect_retrieval_forbidden_deployments_v1,
)
from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
    get_retrieval_replay_divergence_total_v1,
    normalize_retrieval_query_envelope_for_replay_identity_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_query_audit import CortexRetrievalQueryAudit
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

PHASE07_RETRIEVAL_OBSERVABILITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_OBS01_GATE_ID_V1: Final[str] = "G-P07-OBS-01"

RETRIEVAL_OBSERVABILITY_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-observability-doctrine.md"
)

RETRIEVAL_OBS_ENGINE_BUILD_REF_V1: Final[str] = "retrieval-runtime-v1"

RET_OBS01_RULE_ID_V1: Final[str] = "RET-OBS-01"

RET_OBS02_RULE_ID_V1: Final[str] = "RET-OBS-02"

RET_OBS03_RULE_ID_V1: Final[str] = "RET-OBS-03"

_DEFAULT_OBSERVABILITY_THRESHOLDS_V1: Final[dict[str, int]] = {
    "completeness_critical_percent": 50,
    "replay_divergence_spike_per_hour": 3,
    "max_index_lag_epochs": 2,
    "legality_failure_rate_percent": 1,
}

_DEGRADED_LEGALITY_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "retrieval_degraded",
        "retrieval_partial",
        "retrieval_unverifiable",
        "retrieval_forbidden",
    }
)

_RETRIEVAL_QUERIES_TOTAL_V1: int = 0
_RETRIEVAL_OMISSIONS_TOTAL_V1: int = 0
_RETRIEVAL_LEGALITY_FAILURES_TOTAL_V1: int = 0
_RETRIEVAL_QUERIES_BY_LEGALITY_V1: dict[str, int] = defaultdict(int)
_RETRIEVAL_OMISSIONS_BY_CLASS_V1: dict[str, int] = defaultdict(int)
_RETRIEVAL_LATENCY_MS_SAMPLES_V1: deque[int] = deque(maxlen=512)
_LAST_REPLAY_DIVERGENCE_AT_V1: str | None = None
_TENANT_RECENT_QUERY_ROLLUP_V1: dict[str, deque[dict[str, Any]]] = defaultdict(
    lambda: deque(maxlen=100)
)


class RetrievalObservabilityError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def policy_pack_observability_thresholds_v1(
    pack: Mapping[str, Any] | None = None,
) -> dict[str, int]:
    body = dict(pack or load_retrieval_policy_pack_v1())
    raw = body.get("observability")
    if not isinstance(raw, dict):
        return dict(_DEFAULT_OBSERVABILITY_THRESHOLDS_V1)
    out = dict(_DEFAULT_OBSERVABILITY_THRESHOLDS_V1)
    for key in _DEFAULT_OBSERVABILITY_THRESHOLDS_V1:
        if key in raw:
            out[key] = int(raw[key])
    return out


def get_retrieval_queries_total_v1() -> int:
    return _RETRIEVAL_QUERIES_TOTAL_V1


def get_retrieval_omissions_total_v1() -> int:
    return _RETRIEVAL_OMISSIONS_TOTAL_V1


def get_retrieval_legality_failures_total_v1() -> int:
    return _RETRIEVAL_LEGALITY_FAILURES_TOTAL_V1


def get_retrieval_queries_by_legality_v1() -> dict[str, int]:
    return dict(_RETRIEVAL_QUERIES_BY_LEGALITY_V1)


def get_retrieval_omissions_by_class_v1() -> dict[str, int]:
    return dict(_RETRIEVAL_OMISSIONS_BY_CLASS_V1)


def get_last_replay_divergence_at_v1() -> str | None:
    return _LAST_REPLAY_DIVERGENCE_AT_V1


def _percentile_int(samples: Sequence[int], pct: float) -> int:
    if not samples:
        return 0
    ordered = sorted(int(s) for s in samples)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def snapshot_retrieval_metrics_v1() -> dict[str, Any]:
    """Control-plane metrics snapshot (integers / millis only)."""
    return {
        "retrieval_queries_total": get_retrieval_queries_total_v1(),
        "retrieval_queries_by_legality": get_retrieval_queries_by_legality_v1(),
        "retrieval_omissions_total": get_retrieval_omissions_total_v1(),
        "retrieval_omissions_by_class": get_retrieval_omissions_by_class_v1(),
        "retrieval_latency_ms_p50": _percentile_int(_RETRIEVAL_LATENCY_MS_SAMPLES_V1, 50),
        "retrieval_latency_ms_p95": _percentile_int(_RETRIEVAL_LATENCY_MS_SAMPLES_V1, 95),
        "retrieval_replay_divergence_total": get_retrieval_replay_divergence_total_v1(),
        "retrieval_legality_failures_total": get_retrieval_legality_failures_total_v1(),
    }


def record_retrieval_legality_failure_v1(*, reason: str) -> None:
    global _RETRIEVAL_LEGALITY_FAILURES_TOTAL_V1
    _RETRIEVAL_LEGALITY_FAILURES_TOTAL_V1 += 1
    _RETRIEVAL_OMISSIONS_BY_CLASS_V1[f"legality_failure:{reason}"] += 1


def note_retrieval_replay_divergence_observed_v1() -> str:
    """Update last divergence timestamp (companion to replay equivalence counter)."""
    global _LAST_REPLAY_DIVERGENCE_AT_V1
    ts = datetime.now(timezone.utc).isoformat()
    _LAST_REPLAY_DIVERGENCE_AT_V1 = ts
    return ts


def build_retrieval_query_log_v1(
    *,
    envelope: Mapping[str, Any],
    result: Mapping[str, Any],
    duration_ms: int,
    engine_build_ref: str = RETRIEVAL_OBS_ENGINE_BUILD_REF_V1,
    policy_digest: str | None = None,
) -> dict[str, Any]:
    """Structured execution log — digests and counts only (**RET-OBS-01**)."""
    hits = result.get("hits") or []
    omissions = result.get("omissions") or result.get("retrieval_omission_rows") or []
    return {
        "event": "retrieval_query_executed",
        "retrieval_query_replay_identity": str(
            result.get("retrieval_query_replay_identity") or ""
        ),
        "workload_class": str(envelope.get("workload_class") or ""),
        "intent": str(envelope.get("intent") or ""),
        "execution_partition": str(envelope.get("execution_partition") or "authoritative"),
        "retrieval_legality_class": str(result.get("retrieval_legality_class") or ""),
        "hit_count": len(hits) if isinstance(hits, list) else 0,
        "omission_count": len(omissions) if isinstance(omissions, list) else 0,
        "duration_ms": max(0, int(duration_ms)),
        "engine_build_ref": engine_build_ref,
        "policy_digest": policy_digest or retrieval_policy_pack_digest_v1(),
        "receipt_digest": str(
            (result.get("retrieval_query_receipt") or {}).get("receipt_digest")
            if isinstance(result.get("retrieval_query_receipt"), dict)
            else result.get("receipt_digest")
            or ""
        ),
    }


def hash_retrieval_query_envelope_v1(envelope: Mapping[str, Any]) -> str:
    normalized = normalize_retrieval_query_envelope_for_replay_identity_v1(envelope)
    return hash_reasoning_canonical_json_sha256_v1(normalized)


def persist_retrieval_query_audit_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    result: Mapping[str, Any],
    duration_ms: int,
    operator_user_id: uuid.UUID | str | None = None,
    engine_build_ref: str = RETRIEVAL_OBS_ENGINE_BUILD_REF_V1,
    policy_digest: str | None = None,
) -> CortexRetrievalQueryAudit:
    """Persist ``cortex_retrieval_query_audit`` row."""
    receipt = result.get("retrieval_query_receipt")
    receipt_digest = ""
    if isinstance(receipt, dict):
        receipt_digest = str(receipt.get("receipt_digest") or "")
    if not receipt_digest:
        receipt_digest = str(result.get("receipt_digest") or "")
    hits = result.get("hits") or []
    omissions = result.get("omissions") or result.get("retrieval_omission_rows") or []
    op_id: uuid.UUID | None = None
    if operator_user_id is not None:
        op_id = (
            operator_user_id
            if isinstance(operator_user_id, uuid.UUID)
            else uuid.UUID(str(operator_user_id))
        )
    row = CortexRetrievalQueryAudit(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        receipt_digest=receipt_digest or hash_retrieval_query_envelope_v1(envelope),
        operator_user_id=op_id,
        query_envelope_hash=hash_retrieval_query_envelope_v1(envelope),
        result_legality_class=str(result.get("retrieval_legality_class") or "retrieval_replay_safe"),
        retrieval_query_replay_identity=str(result.get("retrieval_query_replay_identity") or ""),
        workload_class=str(envelope.get("workload_class") or ""),
        intent=str(envelope.get("intent") or ""),
        execution_partition=str(envelope.get("execution_partition") or "authoritative"),
        hit_count=len(hits) if isinstance(hits, list) else 0,
        omission_count=len(omissions) if isinstance(omissions, list) else 0,
        duration_ms=max(0, int(duration_ms)),
        engine_build_ref=engine_build_ref,
        policy_digest=policy_digest or retrieval_policy_pack_digest_v1(),
    )
    session.add(row)
    session.flush()
    return row


def _rollup_recent_queries_v1(tenant_id: uuid.UUID | str) -> dict[str, Any]:
    recent = list(_TENANT_RECENT_QUERY_ROLLUP_V1.get(str(tenant_id), ()))
    if not recent:
        return {"sample_count": 0, "degraded_percent": 0, "by_legality": {}}
    degraded = sum(
        1 for r in recent if str(r.get("retrieval_legality_class")) in _DEGRADED_LEGALITY_CLASSES_V1
    )
    by_leg: dict[str, int] = defaultdict(int)
    for r in recent:
        by_leg[str(r.get("retrieval_legality_class") or "unknown")] += 1
    return {
        "sample_count": len(recent),
        "degraded_percent": int(round(100.0 * degraded / len(recent))),
        "by_legality": dict(by_leg),
    }


def build_r_leg_health_predicates_v1(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """R-LEG predicate snapshot for health strip (**RET-OBS-02**)."""
    precheck = run_retrieval_r_leg_precheck_v1(envelope)
    predicates: list[dict[str, Any]] = []
    for pid in list_retrieval_legality_predicate_ids_v1():
        ok = bool(precheck.get(pid))
        predicates.append(
            {
                "predicate_id": pid,
                "ok": ok,
                "failure_class": None if ok else R_LEG_PREDICATE_FAILURE_CLASS_V1.get(pid),
            }
        )
    return {
        "predicates": predicates,
        "all_passed": all(p["ok"] for p in predicates),
    }


def _count_tcre_jobs_present_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
            )
        )
        or 0
    )


def _count_recent_divergences_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    window_hours: int = 1,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    degraded = (
        session.scalar(
            select(func.count())
            .select_from(CortexRetrievalQueryAudit)
            .where(
                CortexRetrievalQueryAudit.tenant_id == tenant_id,
                CortexRetrievalQueryAudit.created_at >= cutoff,
                CortexRetrievalQueryAudit.result_legality_class == "retrieval_degraded",
            )
        )
        or 0
    )
    return int(degraded)


def evaluate_retrieval_alerts_v1(
    *,
    health: Mapping[str, Any],
    metrics: Mapping[str, Any],
    thresholds: Mapping[str, int],
    tcre_jobs_present: int,
) -> list[dict[str, Any]]:
    """Operator-facing alert evaluation (**RET-OBS-03**)."""
    alerts: list[dict[str, Any]] = []
    completeness = int(health.get("retrieval_completeness_percent") or 0)
    crit_pct = int(thresholds.get("completeness_critical_percent", 50))
    if tcre_jobs_present > 0 and completeness < crit_pct:
        alerts.append(
            {
                "alert_id": "retrieval_critical",
                "severity": "critical",
                "message": f"Retrieval completeness {completeness}% below {crit_pct}% with TCRE jobs present",
            }
        )
    spike = int(thresholds.get("replay_divergence_spike_per_hour", 3))
    recent_div = int(health.get("recent_replay_divergences_1h") or 0)
    if recent_div > spike:
        alerts.append(
            {
                "alert_id": "replay_divergence_spike",
                "severity": "warning",
                "message": f">{spike} replay divergences in the last hour ({recent_div})",
            }
        )
    max_lag = int(thresholds.get("max_index_lag_epochs", 2))
    lag_epochs = int(health.get("index_lag_epochs") or 0)
    if lag_epochs > max_lag:
        alerts.append(
            {
                "alert_id": "index_stale",
                "severity": "warning",
                "message": f"index_lag_epochs={lag_epochs} exceeds policy max {max_lag}",
            }
        )
    fail_rate_limit = int(thresholds.get("legality_failure_rate_percent", 1))
    queries = int(metrics.get("retrieval_queries_total") or 0)
    failures = int(metrics.get("retrieval_legality_failures_total") or 0)
    if queries >= 100:
        rate = int(round(100.0 * failures / queries))
        if rate > fail_rate_limit:
            alerts.append(
                {
                    "alert_id": "legality_failure_burst",
                    "severity": "warning",
                    "message": f"retrieval legality failure rate {rate}% exceeds {fail_rate_limit}%",
                }
            )
    return alerts


def build_retrieval_runtime_health_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Runtime health model for admin health strip."""
    coverage = build_retrieval_coverage_catalog_v1(session, tenant_id=tenant_id)
    stage = project_retrieval_completeness_v1(session, tenant_id=tenant_id)
    metrics = dict(stage.get("metrics") or {})
    rollup = _rollup_recent_queries_v1(tenant_id)
    lag = coverage.get("index_lag_epochs")
    lag_count = 0
    if isinstance(lag, dict):
        lag_count = int(lag.get("stale_epoch_count") or 0)
    last_audit_div = session.scalar(
        select(CortexRetrievalQueryAudit.created_at)
        .where(
            CortexRetrievalQueryAudit.tenant_id == tenant_id,
            CortexRetrievalQueryAudit.result_legality_class == "retrieval_degraded",
        )
        .order_by(CortexRetrievalQueryAudit.created_at.desc())
        .limit(1)
    )
    last_div_at = get_last_replay_divergence_at_v1()
    if last_audit_div is not None:
        audit_iso = last_audit_div.isoformat()
        if not last_div_at or audit_iso > last_div_at:
            last_div_at = audit_iso
    sample_env = envelope or {
        "workload_class": "causal_chain",
        "intent": "inspect",
        "execution_partition": "authoritative",
        "addressing": {"retrieval_lookup_id": "sha256:" + "0" * 64},
        "replay_pins": {
            "index_epoch": "epoch-health-probe",
            "tcre_policy_bundle_digest": "sha256:policy-stub",
            "octs_engine_build_ref": "build-stub",
        },
    }
    r_leg = build_r_leg_health_predicates_v1(sample_env)
    thresholds = policy_pack_observability_thresholds_v1()
    tcre_jobs = _count_tcre_jobs_present_v1(session, tenant_id=tenant_id)
    recent_div = _count_recent_divergences_v1(session, tenant_id=tenant_id)
    metric_snap = snapshot_retrieval_metrics_v1()
    health_body: dict[str, Any] = {
        "schema_version": PHASE07_RETRIEVAL_OBSERVABILITY_RUNTIME_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "substrate_state": coverage.get("substrate_state"),
        "replay_posture": coverage.get("replay_posture"),
        "last_replay_divergence_at": last_div_at,
        "index_epoch": coverage.get("published_index_epoch"),
        "index_lag_epochs": lag_count,
        "degraded_percent": rollup["degraded_percent"],
        "retrieval_completeness_percent": int(metrics.get("retrieval_coverage_percent", 0)),
        "retrieval_provenance_coverage_percent": int(
            metrics.get("retrieval_provenance_coverage_percent", 0)
        ),
        "recent_query_rollup": rollup,
        "recent_replay_divergences_1h": recent_div,
        "r_leg_health": r_leg,
        "metrics": metric_snap,
        "observability_thresholds": thresholds,
        "engine_build_ref": RETRIEVAL_OBS_ENGINE_BUILD_REF_V1,
        "policy_digest": retrieval_policy_pack_digest_v1(),
    }
    health_body["forbidden_deployment_detector"] = detect_retrieval_forbidden_deployments_v1(
        session,
        tenant_id=tenant_id,
    )
    health_body["forbidden_deployments_clear"] = all(
        not row.get("detected") for row in health_body["forbidden_deployment_detector"]
    )
    health_body["active_alerts"] = evaluate_retrieval_alerts_v1(
        health=health_body,
        metrics=metric_snap,
        thresholds=thresholds,
        tcre_jobs_present=tcre_jobs,
    )
    return health_body


def build_retrieval_health_strip_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Compact admin health strip payload."""
    health = build_retrieval_runtime_health_v1(session, tenant_id=tenant_id)
    return {
        "substrate_state": health.get("substrate_state"),
        "replay_posture": health.get("replay_posture"),
        "index_epoch": health.get("index_epoch"),
        "degraded_percent": health.get("degraded_percent"),
        "retrieval_completeness_percent": health.get("retrieval_completeness_percent"),
        "last_replay_divergence_at": health.get("last_replay_divergence_at"),
        "active_alerts": health.get("active_alerts") or [],
        "r_leg_all_passed": (health.get("r_leg_health") or {}).get("all_passed"),
    }


def build_retrieval_observability_catalog_v1() -> dict[str, Any]:
    return {
        "retrieval_observability_runtime_schema_version": (
            PHASE07_RETRIEVAL_OBSERVABILITY_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_OBS01_GATE_ID_V1,
        "spec_ref": RETRIEVAL_OBSERVABILITY_SPEC_REF_V1,
        "rules": [
            {"id": RET_OBS01_RULE_ID_V1, "text": "Integer metrics + structured query logs"},
            {"id": RET_OBS02_RULE_ID_V1, "text": "R-LEG health predicates on health strip"},
            {"id": RET_OBS03_RULE_ID_V1, "text": "Policy-pack alert thresholds"},
        ],
        "metric_names": [
            "retrieval_queries_total",
            "retrieval_queries_by_legality",
            "retrieval_omissions_total",
            "retrieval_omissions_by_class",
            "retrieval_latency_ms_p50",
            "retrieval_latency_ms_p95",
            "retrieval_replay_divergence_total",
            "retrieval_legality_failures_total",
            "retrieval_index_lag_epochs",
            "retrieval_provenance_coverage_percent",
            "retrieval_completeness_percent",
        ],
        "audit_table": "cortex_retrieval_query_audit",
        "default_thresholds": dict(_DEFAULT_OBSERVABILITY_THRESHOLDS_V1),
        "engine_build_ref": RETRIEVAL_OBS_ENGINE_BUILD_REF_V1,
    }


def record_retrieval_query_observability_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    result: Mapping[str, Any],
    duration_ms: int,
    operator_user_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    """Record metrics, audit row, and structured log for one completed query."""
    global _RETRIEVAL_QUERIES_TOTAL_V1, _RETRIEVAL_OMISSIONS_TOTAL_V1
    legality = str(result.get("retrieval_legality_class") or "retrieval_replay_safe")
    _RETRIEVAL_QUERIES_TOTAL_V1 += 1
    _RETRIEVAL_QUERIES_BY_LEGALITY_V1[legality] += 1
    omissions = result.get("omissions") or result.get("retrieval_omission_rows") or []
    if isinstance(omissions, list):
        _RETRIEVAL_OMISSIONS_TOTAL_V1 += len(omissions)
        for om in omissions:
            if isinstance(om, dict):
                rd = str(om.get("retrieval_omission_class") or "unknown")
                _RETRIEVAL_OMISSIONS_BY_CLASS_V1[rd] += 1
    _RETRIEVAL_LATENCY_MS_SAMPLES_V1.append(max(0, int(duration_ms)))
    prov_pct = result.get("provenance_coverage_percent")
    if prov_pct is not None:
        try:
            _TENANT_RECENT_QUERY_ROLLUP_V1[str(tenant_id)].append(
                {
                    "retrieval_legality_class": legality,
                    "provenance_coverage_percent": int(prov_pct),
                }
            )
        except (TypeError, ValueError):
            _TENANT_RECENT_QUERY_ROLLUP_V1[str(tenant_id)].append(
                {"retrieval_legality_class": legality}
            )
    else:
        _TENANT_RECENT_QUERY_ROLLUP_V1[str(tenant_id)].append(
            {"retrieval_legality_class": legality}
        )
    twin = result.get("replay_equivalence_twin")
    if isinstance(twin, dict) and not twin.get("gp07_replay_01_passed"):
        note_retrieval_replay_divergence_observed_v1()
    audit = persist_retrieval_query_audit_v1(
        session,
        tenant_id=tenant_id,
        envelope=envelope,
        result=result,
        duration_ms=duration_ms,
        operator_user_id=operator_user_id,
    )
    log_row = build_retrieval_query_log_v1(
        envelope=envelope,
        result=result,
        duration_ms=duration_ms,
    )
    return {
        "audit_id": str(audit.id),
        "query_log": log_row,
        "metrics": snapshot_retrieval_metrics_v1(),
    }


def _obs_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_OBS01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_obs01_metrics_and_health_static() -> dict[str, Any]:
    """**G-P07-OBS-01** — integer metrics, health fields, audit + log law."""
    errors: list[str] = []
    metrics = snapshot_retrieval_metrics_v1()
    for key in (
        "retrieval_queries_total",
        "retrieval_omissions_total",
        "retrieval_latency_ms_p50",
        "retrieval_latency_ms_p95",
    ):
        if not isinstance(metrics.get(key), int):
            errors.append(f"metric_not_int:{key}")
    log = build_retrieval_query_log_v1(
        envelope={
            "workload_class": "causal_chain",
            "intent": "inspect",
            "execution_partition": "authoritative",
        },
        result={
            "retrieval_query_replay_identity": "sha256:" + "a" * 64,
            "retrieval_legality_class": "retrieval_replay_safe",
            "hits": [{"x": 1}],
            "omissions": [],
            "retrieval_query_receipt": {"receipt_digest": "sha256:" + "b" * 64},
        },
        duration_ms=12,
    )
    for field in (
        "retrieval_query_replay_identity",
        "workload_class",
        "hit_count",
        "duration_ms",
        "engine_build_ref",
        "policy_digest",
    ):
        if field not in log:
            errors.append(f"log_missing:{field}")
    if "hits" in log:
        errors.append("log_must_not_embed_hits")
    env_hash = hash_retrieval_query_envelope_v1(
        {"workload_class": "causal_chain", "intent": "inspect", "addressing": {}}
    )
    if len(str(env_hash)) != 64:
        errors.append("envelope_hash_shape")
    r_leg = build_r_leg_health_predicates_v1(
        {
            "workload_class": "causal_chain",
            "intent": "inspect",
            "execution_partition": "authoritative",
            "addressing": {"causal_chain_id": "c1"},
            "replay_pins": {
                "index_epoch": "e1",
                "tcre_policy_bundle_digest": "sha256:p",
                "octs_engine_build_ref": "b1",
            },
        }
    )
    if not r_leg.get("predicates"):
        errors.append("r_leg_predicates_empty")
    thresholds = policy_pack_observability_thresholds_v1()
    alerts = evaluate_retrieval_alerts_v1(
        health={
            "retrieval_completeness_percent": 40,
            "index_lag_epochs": 5,
            "recent_replay_divergences_1h": 10,
        },
        metrics={"retrieval_queries_total": 200, "retrieval_legality_failures_total": 5},
        thresholds=thresholds,
        tcre_jobs_present=1,
    )
    if not alerts:
        errors.append("expected_alerts")
    cat = build_retrieval_observability_catalog_v1()
    if cat["gate_id"] != GP07_OBS01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    return _obs_meta("gp07_obs01_metrics_and_health", errors)
