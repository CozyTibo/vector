"""Phase 02 Step 8 — trust-state + API contract implementation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.raw_memory_verification_unified import (
    compute_phase02_gates_g1_g7,
    trust_annotation_gate_decisions_from_g1_g7,
)
from vector.infrastructure.db.models.raw_memory_failure_case import RawMemoryFailureCase
from vector.infrastructure.db.models.raw_memory_trust_state import RawMemoryTrustState
from vector.infrastructure.db.models.raw_memory_trust_transition import RawMemoryTrustTransition
from vector.infrastructure.db.models.tenant import Tenant

_GATES = ("G1", "G2", "G3", "G4", "G5", "G6", "G7")


def _severity_for_state(state: str) -> str:
    if state == "corrupted":
        return "S3"
    if state in {"unverifiable", "replay-diverged", "continuity-broken", "lineage-incomplete"}:
        return "S2"
    if state in {"partial", "degraded"}:
        return "S1"
    return "S0"


def _derive_trust_state(
    *,
    gate_results: dict[str, dict[str, str]],
    active_cases: list[RawMemoryFailureCase],
) -> tuple[str, list[str]]:
    reason_codes: list[str] = []
    active_impacts = {c.trust_state_impact for c in active_cases}
    if "corrupted" in active_impacts:
        reason_codes.append("CORRUPTION_SIGNAL")
        return "corrupted", reason_codes
    if "continuity-broken" in active_impacts:
        reason_codes.append("LINEAGE_BREAK_WINDOW")
        return "continuity-broken", reason_codes
    if "replay-diverged" in active_impacts:
        reason_codes.append("REPLAY_FORBIDDEN_DIVERGENCE")
        return "replay-diverged", reason_codes
    if "lineage-incomplete" in active_impacts:
        reason_codes.append("LINEAGE_INCOMPLETE")
        return "lineage-incomplete", reason_codes

    hard_fail = [g for g, r in gate_results.items() if r["decision"] == "hard_fail"]
    soft_fail = [g for g, r in gate_results.items() if r["decision"] == "soft_fail"]
    warn_only = [g for g, r in gate_results.items() if r["decision"] == "warn_only"]
    if hard_fail:
        reason_codes.extend(f"{g}_HARD_FAIL" for g in hard_fail)
        return "unverifiable", reason_codes
    if soft_fail:
        reason_codes.extend(f"{g}_SOFT_FAIL" for g in soft_fail)
        return "degraded", reason_codes
    if warn_only:
        reason_codes.extend(f"{g}_WARN" for g in warn_only)
        return "partial", reason_codes
    return "healthy", reason_codes


def _continuity_gaps(
    tenant_id: uuid.UUID, active_cases: list[RawMemoryFailureCase]
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for c in active_cases:
        gap = {
            "gap_id": c.gap_id,
            "type": c.gap_type,
            "scope": {
                "tenant_id": str(tenant_id),
                "connector": c.scope_connector,
                "resource_type": c.scope_resource_type,
                "source_identity_key": c.scope_source_identity_key,
            },
            "window": {
                "from": c.window_from.isoformat() if c.window_from is not None else None,
                "to": c.window_to.isoformat() if c.window_to is not None else None,
                "interval": "[from,to)",
            },
            "source": c.source,
            "trust_state_impact": c.trust_state_impact,
            "recoverability_class": c.recoverability_class,
            "replay_job_id": c.detail.get("replay_job_id") if isinstance(c.detail, dict) else None,
        }
        gaps.append(gap)
    return gaps


def _blocking_flags(state: str) -> dict[str, bool]:
    return {
        "block_trusted_replay_publish": state
        in {"corrupted", "unverifiable", "replay-diverged", "continuity-broken"},
        "block_trust_claims": state
        in {"corrupted", "unverifiable", "replay-diverged", "continuity-broken"},
        "allow_diagnostic_reads": True,
    }


def build_raw_memory_trust_annotation(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    raw_memory_contracts: dict[str, Any],
    raw_memory_persistence: dict[str, Any],
    raw_memory_temporal: dict[str, Any],
    raw_memory_replay: dict[str, Any],
    raw_memory_query: dict[str, Any],
    raw_memory_failure_recovery: dict[str, Any],
    precomputed_gates_g1_g7: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    active_cases = list(
        session.scalars(
            select(RawMemoryFailureCase).where(
                RawMemoryFailureCase.tenant_id == tenant_id,
                RawMemoryFailureCase.active.is_(True),
            )
        ).all()
    )
    gates_g1_g7 = precomputed_gates_g1_g7 or compute_phase02_gates_g1_g7(
        raw_memory_contracts=raw_memory_contracts,
        raw_memory_persistence=raw_memory_persistence,
        raw_memory_temporal=raw_memory_temporal,
        raw_memory_replay=raw_memory_replay,
        raw_memory_query=raw_memory_query,
        raw_memory_failure_recovery=raw_memory_failure_recovery,
    )
    gates = trust_annotation_gate_decisions_from_g1_g7(gates_g1_g7)
    trust_state, reason_codes = _derive_trust_state(gate_results=gates, active_cases=active_cases)
    severity = _severity_for_state(trust_state)
    now = datetime.now(tz=UTC)
    annotation = {
        "scope": {
            "tenant_id": str(tenant_id),
            "connector": None,
            "time_window": {"from": None, "to": None},
        },
        "trust_state": trust_state,
        "severity": severity,
        "state_reason_codes": reason_codes,
        "replay": {
            "state": raw_memory_replay.get("state"),
            "divergence_class": raw_memory_replay.get("summary", {})
            .get("highest_divergence", {})
            .get("class", "D0"),
        },
        "reconstruction": {
            "state": raw_memory_temporal.get("state"),
            "coverage_percent": 100.0 if raw_memory_temporal.get("passed") else 0.0,
        },
        "provenance": {"state": raw_memory_persistence.get("state")},
        "blocking": _blocking_flags(trust_state),
        "continuity_gaps": _continuity_gaps(tenant_id, active_cases),
        "verification": {
            "last_verified_at": now.isoformat(),
            "gate_results": {k: v["decision"].upper() for k, v in gates.items()},
            "gate_decisions": gates,
        },
    }
    return annotation


def persist_raw_memory_trust_annotation(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    annotation: dict[str, Any],
) -> None:
    tenant_exists = session.scalar(select(Tenant.id).where(Tenant.id == tenant_id).limit(1))
    if tenant_exists is None:
        return
    current = session.get(RawMemoryTrustState, tenant_id)
    old_state = current.trust_state if current is not None else None
    new_state = str(annotation["trust_state"])
    if current is None:
        current = RawMemoryTrustState(
            tenant_id=tenant_id,
            trust_state=new_state,
            severity=str(annotation["severity"]),
            state_reason_codes=list(annotation["state_reason_codes"]),
            gate_results=dict(annotation["verification"]["gate_decisions"]),
            blocking=dict(annotation["blocking"]),
            continuity_gaps=list(annotation["continuity_gaps"]),
            verification=dict(annotation["verification"]),
        )
        session.add(current)
    else:
        current.trust_state = new_state
        current.severity = str(annotation["severity"])
        current.state_reason_codes = list(annotation["state_reason_codes"])
        current.gate_results = dict(annotation["verification"]["gate_decisions"])
        current.blocking = dict(annotation["blocking"])
        current.continuity_gaps = list(annotation["continuity_gaps"])
        current.verification = dict(annotation["verification"])

    if old_state != new_state:
        session.add(
            RawMemoryTrustTransition(
                tenant_id=tenant_id,
                from_state=old_state,
                to_state=new_state,
                severity=str(annotation["severity"]),
                trigger=(
                    annotation["state_reason_codes"][0]
                    if annotation["state_reason_codes"]
                    else "STATE_REEVALUATION"
                ),
                detail={
                    "state_reason_codes": annotation["state_reason_codes"],
                    "gate_results": annotation["verification"]["gate_results"],
                },
            )
        )
    session.flush()


def verify_phase02_step8_trust_api_contract(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    raw_memory_contracts: dict[str, Any],
    raw_memory_persistence: dict[str, Any],
    raw_memory_temporal: dict[str, Any],
    raw_memory_replay: dict[str, Any],
    raw_memory_query: dict[str, Any],
    raw_memory_failure_recovery: dict[str, Any],
    precomputed_gates_g1_g7: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    annotation_1 = build_raw_memory_trust_annotation(
        session,
        tenant_id=tenant_id,
        raw_memory_contracts=raw_memory_contracts,
        raw_memory_persistence=raw_memory_persistence,
        raw_memory_temporal=raw_memory_temporal,
        raw_memory_replay=raw_memory_replay,
        raw_memory_query=raw_memory_query,
        raw_memory_failure_recovery=raw_memory_failure_recovery,
        precomputed_gates_g1_g7=precomputed_gates_g1_g7,
    )
    annotation_2 = build_raw_memory_trust_annotation(
        session,
        tenant_id=tenant_id,
        raw_memory_contracts=raw_memory_contracts,
        raw_memory_persistence=raw_memory_persistence,
        raw_memory_temporal=raw_memory_temporal,
        raw_memory_replay=raw_memory_replay,
        raw_memory_query=raw_memory_query,
        raw_memory_failure_recovery=raw_memory_failure_recovery,
        precomputed_gates_g1_g7=precomputed_gates_g1_g7,
    )
    deterministic = (
        annotation_1["trust_state"] == annotation_2["trust_state"]
        and annotation_1["severity"] == annotation_2["severity"]
        and annotation_1["state_reason_codes"] == annotation_2["state_reason_codes"]
        and annotation_1["verification"]["gate_results"]
        == annotation_2["verification"]["gate_results"]
    )
    required_top = {
        "scope",
        "trust_state",
        "severity",
        "state_reason_codes",
        "replay",
        "reconstruction",
        "provenance",
        "blocking",
        "continuity_gaps",
        "verification",
    }
    required_present = required_top.issubset(annotation_1.keys())
    required_ver = {"last_verified_at", "gate_results", "gate_decisions"}
    required_present = required_present and required_ver.issubset(
        annotation_1["verification"].keys()
    )
    gate_shape_valid = set(annotation_1["verification"]["gate_decisions"].keys()) == set(_GATES)

    gaps_shape_valid = True
    for gap in annotation_1["continuity_gaps"]:
        req = {
            "gap_id",
            "type",
            "scope",
            "window",
            "source",
            "trust_state_impact",
            "recoverability_class",
        }
        if not req.issubset(gap.keys()):
            gaps_shape_valid = False
            break

    persist_raw_memory_trust_annotation(session, tenant_id=tenant_id, annotation=annotation_1)

    checks = [
        {"id": "s8_required_trust_fields_present", "passed": required_present, "detail": None},
        {
            "id": "s8_gate_decision_shape_valid",
            "passed": gate_shape_valid,
            "detail": annotation_1["verification"]["gate_results"],
        },
        {
            "id": "s8_continuity_gap_contract_valid",
            "passed": gaps_shape_valid,
            "detail": {"gap_count": len(annotation_1["continuity_gaps"])},
        },
        {
            "id": "s8_deterministic_transition_logic",
            "passed": deterministic,
            "detail": {"trust_state": annotation_1["trust_state"]},
        },
    ]
    passed = all(c["passed"] for c in checks)
    return {
        "passed": passed,
        "state": annotation_1["trust_state"],
        "checks": checks,
        "annotation": annotation_1,
    }
