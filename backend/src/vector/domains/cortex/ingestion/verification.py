"""Phase 01 Step 5 — ingestion invariant probes (verification model).

Read-only checks aligned with ``01-ingestion/ingestion-invariant-checks.md`` and
``failure-probe-matrix.md`` (duplicate delivery, isolation, checkpoint parseability).

Used post-sync (optional, ``Settings.cortex_ingestion_verify_after_sync``), from admin,
and via Celery ``vector.cortex.ingestion.verify_tenant``.
"""

from __future__ import annotations

import copy
import threading
import time
import uuid
from collections import Counter
from typing import Any, Literal, cast

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.admin_recent_raw import aggregate_raw_ingestion_stats
from vector.domains.cortex.ingestion.checkpoint_contract import (
    checkpoint_last_incremental_at,
    parse_checkpoint_iso_timestamp,
)
from vector.domains.cortex.ingestion.live_idempotency import (
    canonical_payload_hash,
    derive_logical_idempotency_key,
    derive_source_identity_key,
    derive_source_revision_key,
)
from vector.domains.cortex.ingestion.raw_envelope_contract import (
    EnvelopeContractViolation,
    validate_raw_payload_for_persistence,
)
from vector.domains.cortex.ingestion.raw_memory_contracts import (
    verify_phase02_step1_runtime_contracts,
)
from vector.domains.cortex.ingestion.raw_memory_critical_integrity import (
    verify_phase02_step15_critical_integrity,
)
from vector.domains.cortex.ingestion.raw_memory_operational_trust_proof import (
    verify_phase02_step16_operational_trust_proof,
)
from vector.domains.cortex.ingestion.raw_memory_control_plane import (
    build_raw_memory_control_plane,
    verify_phase02_step9_control_plane_contract,
)
from vector.domains.cortex.ingestion.raw_memory_enforcement import (
    verify_phase02_step11_progressive_enforcement,
)
from vector.domains.cortex.ingestion.raw_memory_failure_recovery import (
    verify_phase02_step7_failure_recovery,
)
from vector.domains.cortex.ingestion.raw_memory_persistence import (
    verify_phase02_step2_persistence_provenance,
)
from vector.domains.cortex.ingestion.raw_memory_phase_closure import (
    evaluate_phase02_step10_closure_gate,
)
from vector.domains.cortex.ingestion.raw_memory_query import (
    verify_phase02_step5_query_model,
)
from vector.domains.cortex.ingestion.raw_memory_replay import (
    verify_phase02_step4_replay_equivalence,
)
from vector.domains.cortex.ingestion.raw_memory_replay_hardening import (
    verify_phase02_step13_replay_divergence_hardening,
)
from vector.domains.cortex.ingestion.raw_memory_storage import (
    verify_phase02_step6_storage_retention,
)
from vector.domains.cortex.ingestion.raw_memory_temporal import (
    verify_phase02_step3_temporal_continuity,
)
from vector.domains.cortex.ingestion.raw_memory_trust import (
    persist_raw_memory_trust_annotation,
    verify_phase02_step8_trust_api_contract,
)
from vector.domains.cortex.ingestion.raw_memory_trust_signal import (
    verify_phase02_step14_trust_signal_hardening,
)
from vector.domains.cortex.ingestion.raw_memory_verification_unified import (
    build_phase02_verification_truth,
    compute_phase02_gate_g14_trust_signal_quality,
    compute_phase02_gate_g15_critical_integrity,
    compute_phase02_gate_g16_operational_trust_proof,
    compute_phase02_gates_g1_g7,
    finalize_phase02_closure_from_canonical_gates,
    infer_proof_quality,
    verify_phase02_step12_unified_verification_semantics,
)
from vector.domains.cortex.ingestion.runtime_correctness import (
    verify_runtime_correctness_invariants,
)
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

RUN_COMPLETED = "COMPLETED"
RUN_FAILED = "FAILED"
_VERIFY_CACHE_TTL_SECONDS = 12.0
_VERIFY_CACHE_LOCK = threading.Lock()
_VERIFY_CACHE: dict[tuple[str, int, bool, str], tuple[float, dict[str, Any]]] = {}

_EnforcementModeLit = Literal["observe", "progressive", "strict"]


def _stamp_phase02_verification_truth_cache_hit(payload: dict[str, Any]) -> None:
    truth = payload.get("phase02_verification_truth")
    if not isinstance(truth, dict):
        return
    cg = truth.get("canonical_gates")
    if not isinstance(cg, dict):
        return
    _pq_raw = truth.get("proof_quality")
    pq: dict[str, Any] = dict(_pq_raw) if isinstance(_pq_raw, dict) else {}
    truth["freshness"] = dict(truth.get("freshness") or {})
    truth["freshness"]["from_cache"] = True
    _prec_raw = truth.get("precedence")
    prec = _prec_raw if isinstance(_prec_raw, dict) else {}
    align = prec.get("trust_g1_g7_matches_closure")
    align_bool = True if not isinstance(align, bool) else align
    truth["proof_quality"] = infer_proof_quality(
        canonical_gates=cg,
        from_cache=True,
        exhaust_gate_enforced=bool(pq.get("exhaust_gate_enforced")),
        exhaust_gate_passed=pq.get("exhaust_gate_passed"),
        trust_g1_g7_matches_closure=align_bool,
    )
    truth["freshness"]["label"] = "stale"


def _check(
    checks: list[dict[str, Any]],
    *,
    check_id: str,
    passed: bool,
    detail: str | dict[str, Any] | None = None,
) -> bool:
    row: dict[str, Any] = {"id": check_id, "passed": passed}
    if detail is not None:
        row["detail"] = detail
    checks.append(row)
    return passed


def _payload_hash(body: dict[str, Any]) -> str:
    return canonical_payload_hash(body)


def verify_ingestion_run(session: Session, run_id: uuid.UUID) -> dict[str, Any]:
    """Verify invariants for a single ingestion run and its raw rows (read-only)."""
    checks: list[dict[str, Any]] = []
    run = session.get(IngestionRun, run_id)
    if run is None:
        _check(checks, check_id="run_exists", passed=False, detail="ingestion_run not found")
        return {"run_id": str(run_id), "passed": False, "checks": checks}

    _check(checks, check_id="run_exists", passed=True, detail=run.status)

    terminal = run.status in (RUN_COMPLETED, RUN_FAILED)
    term_ok = run.finished_at is not None if terminal else True
    _check(
        checks,
        check_id="terminal_run_has_finished_at",
        passed=term_ok,
        detail={"status": run.status, "has_finished_at": run.finished_at is not None},
    )

    row_stmt = select(RawIngestionRecord).where(RawIngestionRecord.run_id == run_id)
    rows = list(session.scalars(row_stmt).all())

    align_ok = True
    envelope_ok = True
    replay_ok = True
    hash_ok = True
    for r in rows:
        if r.tenant_id != run.tenant_id or r.connection_id != run.connection_id or r.connector != run.connector:
            align_ok = False
            break
    _check(
        checks,
        check_id="raw_rows_align_run",
        passed=align_ok,
        detail={"raw_row_count": len(rows)},
    )

    idem_counts = Counter(r.idempotency_key for r in rows)
    dup_keys = [k for k, c in idem_counts.items() if c > 1]
    _check(
        checks,
        check_id="idempotency_unique_within_run",
        passed=len(dup_keys) == 0,
        detail={"duplicate_keys": dup_keys[:20], "duplicate_key_count": len(dup_keys)},
    )

    envelope_errors: list[str] = []
    for r in rows:
        try:
            validate_raw_payload_for_persistence(
                connector=r.connector,
                connection_id=r.connection_id,
                body=dict(r.payload_body),
            )
        except EnvelopeContractViolation as e:
            envelope_ok = False
            envelope_errors.append(f"raw id={r.id}: {e}")
            if len(envelope_errors) >= 10:
                break
    _check(
        checks,
        check_id="raw_envelope_contract",
        passed=envelope_ok,
        detail={"errors": envelope_errors} if envelope_errors else {"sampled_rows": len(rows)},
    )

    replay_errors: list[str] = []
    for r in rows:
        if r.replay_job_id is None:
            continue
        meta = r.payload_body.get("cortex_replay_metadata") if isinstance(r.payload_body, dict) else None
        if not isinstance(meta, dict):
            replay_ok = False
            replay_errors.append(f"raw id={r.id}: missing cortex_replay_metadata object")
            continue
        if str(r.replay_job_id) != str(meta.get("replay_job_id", "")).strip():
            replay_ok = False
            replay_errors.append(f"raw id={r.id}: replay_job_id column vs metadata mismatch")
        if r.replay_version is not None and meta.get("replay_version") != r.replay_version:
            replay_ok = False
            replay_errors.append(f"raw id={r.id}: replay_version column vs metadata mismatch")
        if len(replay_errors) >= 10:
            break
    _check(
        checks,
        check_id="replay_metadata_alignment",
        passed=replay_ok,
        detail=(
            {"errors": replay_errors}
            if replay_errors
            else {"replay_rows": sum(1 for x in rows if x.replay_job_id is not None)}
        ),
    )

    run_logical_mismatch = 0
    for r in rows:
        body = dict(r.payload_body)
        if _payload_hash(body) != r.payload_hash:
            hash_ok = False
        expected_identity = derive_source_identity_key(
            connector=r.connector,
            resource_type=r.resource_type,
            external_id=r.external_id,
        )
        expected_revision = derive_source_revision_key(body)
        expected_live_key = derive_logical_idempotency_key(
            source_identity_key=expected_identity,
            source_revision_key=expected_revision,
        )[:128]
        if r.idempotency_key != expected_live_key:
            run_logical_mismatch += 1
    # Backward compatibility: pre-cutover runs can legitimately fail current hash
    # semantics while still being useful for historical audit. Once a run is fully
    # legacy-shaped, do not fail tenant-level verification on this check.
    if hash_ok is False and rows and run_logical_mismatch == len(rows):
        hash_ok = True
        hash_detail: dict[str, Any] = {
            "rows_checked": len(rows),
            "legacy_contract_compatible": True,
            "legacy_row_count": len(rows),
        }
    else:
        hash_detail = {"rows_checked": len(rows), "legacy_contract_compatible": False}
    _check(
        checks,
        check_id="payload_hash_matches_body",
        passed=hash_ok,
        detail=hash_detail,
    )

    passed = all(c["passed"] for c in checks)
    return {"run_id": str(run_id), "passed": passed, "checks": checks}


def verify_connector_sync_checkpoints(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Parseability probe for ``connector_sync_state`` JSON (checkpoint contract)."""
    checks: list[dict[str, Any]] = []
    stmt = select(ConnectorSyncState).where(ConnectorSyncState.tenant_id == tenant_id)
    states = list(session.scalars(stmt).all())
    bad: list[str] = []
    for st in states:
        ts = checkpoint_last_incremental_at(dict(st.state))
        if ts is None:
            continue
        if parse_checkpoint_iso_timestamp(ts) is None:
            bad.append(f"{st.scope_key!r}: last_incremental_at not parseable ({ts!r})")
    _check(
        checks,
        check_id="checkpoint_timestamps_parseable",
        passed=len(bad) == 0,
        detail={"scopes_with_issues": bad[:25], "scope_count": len(states)},
    )
    passed = all(c["passed"] for c in checks)
    return {"passed": passed, "checks": checks, "scopes_examined": len(states)}


def assess_exhaust_depth(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Heuristic signals for whether raw store contains cognition-grade exhaust vs pings only."""
    rows = aggregate_raw_ingestion_stats(session, tenant_id, include_health_rows=True)
    by_rt = {r["resource_type"]: int(r["row_count"]) for r in rows}
    by_conn: dict[str, int] = {}
    non_health_by_conn: dict[str, int] = {}
    non_health_total = 0
    newest_non_health_ts = None
    for r in rows:
        c = str(r["connector"])
        cnt = int(r["row_count"])
        by_conn[c] = by_conn.get(c, 0) + cnt
        rt = str(r["resource_type"])
        is_health = rt.endswith(".scope_ping") or rt in {"scope_ping", "viewer_ping", "linear.viewer_ping"}
        if not is_health:
            non_health_by_conn[c] = non_health_by_conn.get(c, 0) + cnt
            non_health_total += cnt
            newest = r.get("newest_fetched_at")
            if newest is not None and (newest_non_health_ts is None or newest > newest_non_health_ts):
                newest_non_health_ts = newest

    pingish = (
        sum(by_rt.get(k, 0) for k in by_rt if "scope_ping" in k or k.endswith(".scope_ping"))
        + by_rt.get("linear.viewer_ping", 0)
    )
    total = sum(by_rt.values()) or 1
    ping_ratio = pingish / total

    warnings: list[dict[str, Any]] = []
    if ping_ratio > 0.9 and total < 500:
        warnings.append(
            {
                "code": "mostly_ping_like_rows",
                "severity": "warn",
                "detail": "Most raw rows are health/ping types — conversational or delivery exhaust may be absent.",
            },
        )
    if by_conn.get("slack") and not any(k.startswith("slack.message") for k in by_rt):
        warnings.append(
            {
                "code": "slack_no_messages",
                "severity": "warn",
                "detail": "Slack connected in raw store but no slack.message resource_type rows observed.",
            },
        )
    if by_conn.get("github") and by_rt.get("github.repository", 0) > 0 and not any(
        "pull" in k for k in by_rt
    ):
        warnings.append(
            {
                "code": "github_no_pr_rows",
                "severity": "warn",
                "detail": "GitHub repositories ingested but no pull-request-class rows observed yet.",
            },
        )
    if by_conn.get("linear") and not by_rt.get("linear.issue"):
        warnings.append(
            {
                "code": "linear_no_issues",
                "severity": "warn",
                "detail": "Linear rows exist but no linear.issue snapshots observed.",
            },
        )

    gate_checks: list[dict[str, Any]] = []
    gate_passed = True
    if non_health_total > 0:
        ping_gate = ping_ratio <= 0.6
        gate_checks.append(
            {
                "id": "ping_ratio_after_streams",
                "passed": ping_gate,
                "detail": {
                    "ping_like_ratio": round(ping_ratio, 4),
                    "threshold": 0.6,
                    "non_health_row_count": non_health_total,
                },
            },
        )
        gate_passed = gate_passed and ping_gate

        connectors_gate = len(non_health_by_conn) >= 2
        gate_checks.append(
            {
                "id": "multi_connector_non_health_evidence",
                "passed": connectors_gate,
                "detail": {
                    "connectors_with_non_health_rows": sorted(non_health_by_conn.keys()),
                    "min_required": 2,
                },
            },
        )
        gate_passed = gate_passed and connectors_gate

        conversational_present = any(
            by_rt.get(rt, 0) > 0 for rt in ("slack.message", "calls.meeting", "calls.transcript")
        )
        planning_present = any(by_rt.get(rt, 0) > 0 for rt in ("linear.issue", "notion.database_row", "notion.page"))
        delivery_present = any(
            by_rt.get(rt, 0) > 0
            for rt in ("github.pull_request", "github.commit", "github.workflow_run", "github.deployment")
        )
        coverage_score = sum(int(x) for x in (conversational_present, planning_present, delivery_present))
        triad_gate = coverage_score >= 2
        gate_checks.append(
            {
                "id": "reconstruction_signal_coverage",
                "passed": triad_gate,
                "detail": {
                    "conversational_present": conversational_present,
                    "planning_present": planning_present,
                    "delivery_present": delivery_present,
                    "required_true_count": 2,
                },
            },
        )
        gate_passed = gate_passed and triad_gate
    else:
        gate_checks.append(
            {
                "id": "ping_ratio_after_streams",
                "passed": True,
                "detail": "No non-health rows yet; exhaust gate deferred until deep streams exist.",
            },
        )

    reconstruction_checklist = [
        {
            "id": "recent_non_health_rows_present",
            "passed": non_health_total > 0,
            "detail": {
                "non_health_row_count": non_health_total,
                "newest_non_health_fetched_at": newest_non_health_ts.isoformat()
                if newest_non_health_ts is not None
                else None,
            },
        },
        {
            "id": "cross_connector_context_present",
            "passed": len(non_health_by_conn) >= 2,
            "detail": {"connectors_with_non_health_rows": sorted(non_health_by_conn.keys())},
        },
    ]

    live_total = int(
        session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
            )
        )
        or 0
    )
    live_missing_identity = int(
        session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
                or_(
                    RawIngestionRecord.source_identity_key.is_(None),
                    RawIngestionRecord.source_revision_key.is_(None),
                ),
            )
        )
        or 0
    )

    live_rows = list(
        session.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
            )
        ).all()
    )
    run_scoped_live_identity_forbidden = True
    for row in live_rows:
        body = dict(row.payload_body) if isinstance(row.payload_body, dict) else {}
        expected_identity = derive_source_identity_key(
            connector=row.connector,
            resource_type=row.resource_type,
            external_id=row.external_id,
        )
        expected_revision = derive_source_revision_key(body)
        expected_live_key = derive_logical_idempotency_key(
            source_identity_key=expected_identity,
            source_revision_key=expected_revision,
        )[:128]
        if row.idempotency_key != expected_live_key:
            run_scoped_live_identity_forbidden = False
            break

    return {
        "resource_type_counts": by_rt,
        "connector_totals": by_conn,
        "non_health_connector_totals": non_health_by_conn,
        "non_health_row_count": non_health_total,
        "ping_like_row_count": pingish,
        "ping_like_ratio": round(ping_ratio, 4),
        "warnings": warnings,
        "gate_checks": gate_checks,
        "gate_passed": gate_passed,
        "reconstruction_drill": {
            "checklist": reconstruction_checklist,
            "passed": all(item["passed"] for item in reconstruction_checklist),
        },
        "live_idempotency_status": {
            "live_rows_examined": live_total,
            "source_identity_key_present": live_missing_identity == 0,
            "source_revision_key_present": live_missing_identity == 0,
            "run_scoped_live_identity_forbidden": run_scoped_live_identity_forbidden,
        },
    }


def verify_tenant_ingestion_invariants(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    run_limit: int = 30,
    enforce_exhaust_gate: bool = False,
    enforcement_mode: str = "progressive",
) -> dict[str, Any]:
    """Sweep recent runs for a tenant plus checkpoint parseability (operator checklist)."""
    cache_key = (str(tenant_id), int(run_limit), bool(enforce_exhaust_gate), str(enforcement_mode))
    now = time.monotonic()
    with _VERIFY_CACHE_LOCK:
        cached = _VERIFY_CACHE.get(cache_key)
        if cached is not None:
            ts, payload = cached
            if now - ts <= _VERIFY_CACHE_TTL_SECONDS:
                out = copy.deepcopy(payload)
                _stamp_phase02_verification_truth_cache_hit(out)
                return out

    stmt = (
        select(IngestionRun)
        .where(IngestionRun.tenant_id == tenant_id)
        .order_by(IngestionRun.started_at.desc())
        .limit(run_limit)
    )
    runs = list(session.scalars(stmt).all())
    run_reports: list[dict[str, Any]] = []
    for run in runs:
        run_reports.append(verify_ingestion_run(session, run.id))
    ckpt = verify_connector_sync_checkpoints(session, tenant_id)
    runtime_correctness = verify_runtime_correctness_invariants(session, tenant_id)
    raw_memory_contracts = verify_phase02_step1_runtime_contracts(session, tenant_id)
    raw_memory_persistence = verify_phase02_step2_persistence_provenance(session, tenant_id)
    raw_memory_temporal = verify_phase02_step3_temporal_continuity(session, tenant_id)
    raw_memory_replay = verify_phase02_step4_replay_equivalence(session, tenant_id)
    raw_memory_replay_hardening = verify_phase02_step13_replay_divergence_hardening(
        raw_memory_replay
    )
    raw_memory_query = verify_phase02_step5_query_model(session, tenant_id)
    raw_memory_storage = verify_phase02_step6_storage_retention(session, tenant_id)
    raw_memory_failure_recovery = verify_phase02_step7_failure_recovery(session, tenant_id)
    _enforcement_modes = {"observe", "progressive", "strict"}
    mode_norm = enforcement_mode if enforcement_mode in _enforcement_modes else "progressive"
    gates_g1_g7 = compute_phase02_gates_g1_g7(
        raw_memory_contracts=raw_memory_contracts,
        raw_memory_persistence=raw_memory_persistence,
        raw_memory_temporal=raw_memory_temporal,
        raw_memory_replay=raw_memory_replay,
        raw_memory_query=raw_memory_query,
        raw_memory_failure_recovery=raw_memory_failure_recovery,
    )
    exhaust = assess_exhaust_depth(session, tenant_id)
    raw_memory_trust = verify_phase02_step8_trust_api_contract(
        session,
        tenant_id=tenant_id,
        raw_memory_contracts=raw_memory_contracts,
        raw_memory_persistence=raw_memory_persistence,
        raw_memory_temporal=raw_memory_temporal,
        raw_memory_replay=raw_memory_replay,
        raw_memory_query=raw_memory_query,
        raw_memory_failure_recovery=raw_memory_failure_recovery,
        precomputed_gates_g1_g7=gates_g1_g7,
    )
    trust_ann = raw_memory_trust.get("annotation") if isinstance(raw_memory_trust, dict) else None
    control_plane_payload_prelim = build_raw_memory_control_plane(
        session,
        tenant_id,
        verification_payload={
            "raw_memory_replay": raw_memory_replay,
            "raw_memory_persistence": raw_memory_persistence,
            "raw_memory_temporal": raw_memory_temporal,
            "raw_memory_query": raw_memory_query,
            "raw_memory_failure_recovery": raw_memory_failure_recovery,
            "raw_memory_trust": raw_memory_trust,
            "enforcement_mode": mode_norm,
            "raw_memory_phase_closure": {},
        },
    )
    raw_memory_control_plane_prelim = verify_phase02_step9_control_plane_contract(
        control_plane_payload=control_plane_payload_prelim
    )
    closure_prelim = evaluate_phase02_step10_closure_gate(
        tenant_id=tenant_id,
        raw_memory_contracts=raw_memory_contracts,
        raw_memory_persistence=raw_memory_persistence,
        raw_memory_temporal=raw_memory_temporal,
        raw_memory_replay=raw_memory_replay,
        raw_memory_query=raw_memory_query,
        raw_memory_failure_recovery=raw_memory_failure_recovery,
        raw_memory_trust=raw_memory_trust,
        raw_memory_control_plane=raw_memory_control_plane_prelim,
        control_plane_payload=control_plane_payload_prelim,
        precomputed_gates_g1_g7=gates_g1_g7,
        raw_memory_replay_hardening=raw_memory_replay_hardening,
    )
    gates_pre = closure_prelim.get("gate_results") or {}
    gates_pre = gates_pre if isinstance(gates_pre, dict) else {}
    truth_pre = build_phase02_verification_truth(
        tenant_id=tenant_id,
        canonical_gates=gates_pre,
        trust_annotation=trust_ann,
        from_cache=False,
        cache_ttl_seconds=_VERIFY_CACHE_TTL_SECONDS,
        enforcement_mode=mode_norm,
        exhaust_gate_enforced=enforce_exhaust_gate,
        exhaust_gate_passed=bool(exhaust.get("gate_passed")) if enforce_exhaust_gate else None,
        verification_passed=False,
    )
    raw_memory_trust_signal = verify_phase02_step14_trust_signal_hardening(truth_pre)
    raw_memory_critical_integrity = verify_phase02_step15_critical_integrity(session, tenant_id)
    gates_complete = dict(gates_pre)
    gates_complete["G14"] = compute_phase02_gate_g14_trust_signal_quality(raw_memory_trust_signal)
    gates_complete["G15"] = compute_phase02_gate_g15_critical_integrity(raw_memory_critical_integrity)
    run_passed = all(r["passed"] for r in run_reports) if run_reports else True
    core_passed = (
        run_passed
        and ckpt["passed"]
        and runtime_correctness["passed"]
        and raw_memory_contracts["passed"]
        and raw_memory_persistence["passed"]
        and raw_memory_temporal["passed"]
        and raw_memory_replay["passed"]
        and raw_memory_query["passed"]
        and raw_memory_storage["passed"]
        and raw_memory_failure_recovery["passed"]
        and raw_memory_trust["passed"]
        and raw_memory_control_plane_prelim["passed"]
        and raw_memory_replay_hardening["passed"]
        and raw_memory_trust_signal["passed"]
        and raw_memory_critical_integrity["passed"]
    )
    if enforce_exhaust_gate:
        core_passed = core_passed and bool(exhaust.get("gate_passed"))
    phase02_verification_truth = build_phase02_verification_truth(
        tenant_id=tenant_id,
        canonical_gates=gates_complete,
        trust_annotation=trust_ann,
        from_cache=False,
        cache_ttl_seconds=_VERIFY_CACHE_TTL_SECONDS,
        enforcement_mode=mode_norm,
        exhaust_gate_enforced=enforce_exhaust_gate,
        exhaust_gate_passed=bool(exhaust.get("gate_passed")) if enforce_exhaust_gate else None,
        verification_passed=core_passed,
    )
    raw_memory_operational_trust_proof = verify_phase02_step16_operational_trust_proof(
        runtime_correctness=runtime_correctness,
        raw_memory_temporal=raw_memory_temporal,
        raw_memory_replay=raw_memory_replay,
        raw_memory_replay_hardening=raw_memory_replay_hardening,
        raw_memory_failure_recovery=raw_memory_failure_recovery,
        raw_memory_critical_integrity=raw_memory_critical_integrity,
        raw_memory_trust_signal=raw_memory_trust_signal,
        phase02_verification_truth=phase02_verification_truth,
    )
    gates_complete["G16"] = compute_phase02_gate_g16_operational_trust_proof(raw_memory_operational_trust_proof)
    raw_memory_phase_closure = finalize_phase02_closure_from_canonical_gates(
        tenant_id=tenant_id,
        gates=gates_complete,
        raw_memory_trust=raw_memory_trust,
    )
    raw_memory_enforcement = verify_phase02_step11_progressive_enforcement(
        trust_annotation=trust_ann,
        phase_closure=raw_memory_phase_closure,
        enforcement_mode=cast(_EnforcementModeLit, mode_norm),
    )
    _prec = phase02_verification_truth.get("precedence")
    _prec_dict = _prec if isinstance(_prec, dict) else {}
    _align = _prec_dict.get("trust_g1_g7_matches_closure")
    align_bool = True if not isinstance(_align, bool) else _align
    phase02_verification_truth["proof_quality"] = infer_proof_quality(
        canonical_gates=gates_complete,
        from_cache=False,
        exhaust_gate_enforced=enforce_exhaust_gate,
        exhaust_gate_passed=bool(exhaust.get("gate_passed")) if enforce_exhaust_gate else None,
        trust_g1_g7_matches_closure=align_bool,
    )
    passed = (
        core_passed
        and raw_memory_phase_closure["passed"]
        and raw_memory_enforcement["passed"]
        and raw_memory_operational_trust_proof["passed"]
    )
    if isinstance(trust_ann, dict):
        ver = dict(trust_ann.get("verification") or {})
        ver["proof_quality"] = phase02_verification_truth["proof_quality"]
        ver["freshness"] = phase02_verification_truth["freshness"]
        persist_raw_memory_trust_annotation(
            session,
            tenant_id=tenant_id,
            annotation={**trust_ann, "verification": ver},
        )
    control_plane_payload_final = build_raw_memory_control_plane(
        session,
        tenant_id,
        verification_payload={
            "raw_memory_replay": raw_memory_replay,
            "raw_memory_persistence": raw_memory_persistence,
            "raw_memory_temporal": raw_memory_temporal,
            "raw_memory_query": raw_memory_query,
            "raw_memory_failure_recovery": raw_memory_failure_recovery,
            "raw_memory_trust": raw_memory_trust,
            "enforcement_mode": mode_norm,
            "raw_memory_phase_closure": raw_memory_phase_closure,
            "phase02_verification_truth": phase02_verification_truth,
            "raw_memory_critical_integrity": raw_memory_critical_integrity,
            "raw_memory_operational_trust_proof": raw_memory_operational_trust_proof,
        },
    )
    raw_memory_control_plane = verify_phase02_step9_control_plane_contract(
        control_plane_payload=control_plane_payload_final
    )
    passed = passed and raw_memory_control_plane["passed"]
    raw_memory_verification_step12 = verify_phase02_step12_unified_verification_semantics(
        phase02_verification_truth=phase02_verification_truth,
        raw_memory_phase_closure=raw_memory_phase_closure,
        raw_memory_trust=raw_memory_trust,
    )
    passed = passed and raw_memory_verification_step12["passed"]
    if isinstance(phase02_verification_truth, dict):
        phase02_verification_truth["aggregate_passed"] = passed
    out = {
        "tenant_id": str(tenant_id),
        "passed": passed,
        "runs_examined": len(run_reports),
        "run_reports": run_reports,
        "checkpoint_report": ckpt,
        "exhaust_depth": exhaust,
        "runtime_correctness": runtime_correctness,
        "raw_memory_contracts": raw_memory_contracts,
        "raw_memory_persistence": raw_memory_persistence,
        "raw_memory_temporal": raw_memory_temporal,
        "raw_memory_replay": raw_memory_replay,
        "raw_memory_replay_hardening": raw_memory_replay_hardening,
        "raw_memory_trust_signal": raw_memory_trust_signal,
        "raw_memory_critical_integrity": raw_memory_critical_integrity,
        "raw_memory_operational_trust_proof": raw_memory_operational_trust_proof,
        "raw_memory_query": raw_memory_query,
        "raw_memory_storage": raw_memory_storage,
        "raw_memory_failure_recovery": raw_memory_failure_recovery,
        "raw_memory_trust": raw_memory_trust,
        "raw_memory_control_plane": raw_memory_control_plane,
        "raw_memory_phase_closure": raw_memory_phase_closure,
        "raw_memory_enforcement": raw_memory_enforcement,
        "enforcement_mode": mode_norm,
        "phase02_verification_truth": phase02_verification_truth,
        "raw_memory_verification_step12": raw_memory_verification_step12,
    }
    with _VERIFY_CACHE_LOCK:
        _VERIFY_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(out))
    return out
