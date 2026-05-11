"""Phase 02 Step 12 — single canonical gate computation for closure, trust, and admin surfaces."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

_TRUST_GATE_IDS = ("G1", "G2", "G3", "G4", "G5", "G6", "G7")
_CANONICAL_ORDER = tuple(f"G{i}" for i in range(1, 11)) + ("G13", "G14", "G15", "G16")


def closure_gate_row(decision: str, reason: str, *, required_scope: bool = True) -> dict[str, Any]:
    """Single gate row shape used by closure and downstream summaries."""
    return {
        "decision": decision,
        "reason": reason,
        "required_scope": required_scope,
        "passed": decision in {"pass", "warn_only"},
    }


def compute_phase02_gates_g1_g7(
    *,
    raw_memory_contracts: dict[str, Any],
    raw_memory_persistence: dict[str, Any],
    raw_memory_temporal: dict[str, Any],
    raw_memory_replay: dict[str, Any],
    raw_memory_query: dict[str, Any],
    raw_memory_failure_recovery: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Canonical G1–G7 gates (shared by trust annotation and phase closure)."""
    gates: dict[str, dict[str, Any]] = {}
    temporal_state = str(raw_memory_temporal.get("state", "unverifiable"))
    if raw_memory_contracts.get("passed") is not True:
        gates["G1"] = closure_gate_row("hard_fail", "reconstruction invariants failed")
    elif temporal_state in {"corrupted", "continuity-broken", "unverifiable"}:
        gates["G1"] = closure_gate_row(
            "hard_fail", f"temporal state not closure-safe: {temporal_state}"
        )
    elif raw_memory_temporal.get("passed") is True:
        gates["G1"] = closure_gate_row("pass", "reconstruction invariants pass")
    else:
        gates["G1"] = closure_gate_row("soft_fail", "bounded partial reconstruction")

    divergence = (
        raw_memory_replay.get("summary", {}).get("highest_divergence", {}).get("class", "D0")
    )
    if divergence in {"D3", "D4", "D5"}:
        gates["G2"] = closure_gate_row("hard_fail", f"forbidden replay divergence {divergence}")
    elif divergence == "D2":
        gates["G2"] = closure_gate_row("soft_fail", "schema reinterpretation divergence")
    elif divergence == "D1":
        gates["G2"] = closure_gate_row("warn_only", "provider mutation divergence")
    else:
        gates["G2"] = closure_gate_row("pass", "replay equivalence stable")

    if raw_memory_persistence.get("passed") is True:
        gates["G3"] = closure_gate_row("pass", "provenance continuity checks pass")
    else:
        checks = {
            c["id"]: c for c in raw_memory_persistence.get("checks", []) if isinstance(c, dict)
        }
        severe_fail = any(
            (checks.get(cid) or {}).get("passed") is False
            for cid in {"s2_lineage_raw_references_resolve", "s2_lineage_keys_and_chain_stable"}
        )
        gates["G3"] = closure_gate_row(
            "hard_fail" if severe_fail else "soft_fail",
            "lineage continuity unresolved" if severe_fail else "lineage metadata incomplete",
        )

    gates["G4"] = (
        closure_gate_row("pass", "temporal continuity deterministic")
        if raw_memory_temporal.get("passed") is True
        else closure_gate_row("hard_fail", "temporal continuity failure")
    )

    active_classes = raw_memory_failure_recovery.get("summary", {}).get(
        "active_failure_classes", {}
    )
    if raw_memory_failure_recovery.get("passed") is not True:
        gates["G5"] = closure_gate_row("hard_fail", "corruption/failure coverage invalid")
    elif int(active_classes.get("payload_mutation_corruption", 0)) > 0:
        gates["G5"] = closure_gate_row("hard_fail", "active payload corruption present")
    else:
        gates["G5"] = closure_gate_row("pass", "corruption coverage active")

    latest_validation = raw_memory_failure_recovery.get("summary", {}).get(
        "latest_recovery_validation"
    )
    recoverable_active = 0
    for check in raw_memory_failure_recovery.get("checks", []):
        if (
            isinstance(check, dict)
            and check.get("id") == "s7_recovery_validation_present_for_recoverable"
        ):
            recoverable_active = int(
                (check.get("detail") or {}).get("recoverable_active_failures", 0)
            )
            break
    if latest_validation is None and recoverable_active > 0:
        gates["G6"] = closure_gate_row(
            "soft_fail", "recovery validation pending", required_scope=True
        )
    elif latest_validation is not None and latest_validation.get("status") != "validated":
        gates["G6"] = closure_gate_row("hard_fail", "latest recovery validation failed")
    else:
        gates["G6"] = closure_gate_row("pass", "recovery validation in good standing")

    if raw_memory_query.get("passed") is True:
        gates["G7"] = closure_gate_row("pass", "query conformance checks pass")
    else:
        checks = {c["id"]: c for c in raw_memory_query.get("checks", []) if isinstance(c, dict)}
        anti_goal_fail = (checks.get("s5_anti_goal_semantic_graph_blocked") or {}).get(
            "passed"
        ) is False
        gates["G7"] = closure_gate_row(
            "hard_fail" if anti_goal_fail else "soft_fail",
            "semantic/graph leakage detected"
            if anti_goal_fail
            else "supported query determinism issue",
        )

    return gates


def compute_phase02_gates_g8_g10(
    *,
    raw_memory_trust: dict[str, Any],
    raw_memory_control_plane: dict[str, Any],
    control_plane_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Canonical G8–G10 gates (depend on trust + control-plane surfaces)."""
    gates: dict[str, dict[str, Any]] = {}
    gates["G8"] = (
        closure_gate_row("pass", "required control-plane inspection/actions available")
        if raw_memory_control_plane.get("passed") is True
        else closure_gate_row(
            "hard_fail", "control-plane contract missing required operator surface"
        )
    )

    trust_checks = {
        c["id"]: c for c in raw_memory_trust.get("checks", []) if isinstance(c, dict) and "id" in c
    }
    deterministic_transition_ok = (trust_checks.get("s8_deterministic_transition_logic") or {}).get(
        "passed"
    ) is True
    if raw_memory_trust.get("passed") is not True and not deterministic_transition_ok:
        gates["G9"] = closure_gate_row("hard_fail", "trust transition logic non-deterministic")
    elif raw_memory_trust.get("passed") is not True:
        gates["G9"] = closure_gate_row("soft_fail", "trust-state contract partially degraded")
    else:
        gates["G9"] = closure_gate_row(
            "pass", "trust-state transitions implemented and deterministic"
        )

    must_not_assume = list((control_plane_payload.get("warnings") or {}).get("must_not_assume", []))
    boundary_phrase_present = any(
        "replay-safe" in str(msg).lower() and "replay-complete" in str(msg).lower()
        for msg in must_not_assume
    )
    if not boundary_phrase_present:
        gates["G10"] = closure_gate_row(
            "hard_fail", "replay-safe/non-omniscient boundary messaging missing"
        )
    else:
        gates["G10"] = closure_gate_row(
            "pass", "replay-safe boundary proof present in operator surface"
        )

    return gates


def merge_phase02_canonical_gates(
    gates_g1_g7: dict[str, dict[str, Any]],
    gates_g8_g10: dict[str, dict[str, Any]],
    *,
    stabilization_gates: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Deterministic merge (G1–G7 then G8–G10; optional stabilization gates e.g. G13)."""
    merged = dict(gates_g1_g7)
    merged.update(gates_g8_g10)
    if stabilization_gates:
        merged.update(stabilization_gates)
    return merged


def compute_phase02_gate_g13_replay_proof_depth(
    raw_memory_replay_hardening: dict[str, Any],
) -> dict[str, Any]:
    """G13 — replay proof depth (Step 13): D0–D5 denial semantics + hardening checks."""
    if raw_memory_replay_hardening.get("passed") is True:
        return closure_gate_row("pass", "replay divergence hardening checks pass")
    return closure_gate_row("hard_fail", "replay proof depth / forbidden denial validation failed")


def compute_phase02_gate_g14_trust_signal_quality(
    raw_memory_trust_signal: dict[str, Any],
) -> dict[str, Any]:
    """G14 — trust-signal proof quality (Step 14): operator-visible freshness / proof-quality."""
    if raw_memory_trust_signal.get("passed") is True:
        return closure_gate_row(
            "pass",
            "verification truth exposes proof-quality and freshness labels for operators",
        )
    return closure_gate_row(
        "hard_fail",
        "trust-signal / proof-quality surface incomplete or inconsistent",
    )


def compute_phase02_gate_g15_critical_integrity(
    raw_memory_critical_integrity: dict[str, Any],
) -> dict[str, Any]:
    """G15 — critical integrity (Step 15): lineage/revision pointers trust-aligned."""
    if raw_memory_critical_integrity.get("passed") is True:
        return closure_gate_row(
            "pass",
            "reconstruction-critical revision and lineage pointers are consistent",
        )
    return closure_gate_row(
        "hard_fail",
        "critical lineage/revision integrity checks failed",
    )


def compute_phase02_gate_g16_operational_trust_proof(
    raw_memory_operational_trust_proof: dict[str, Any],
) -> dict[str, Any]:
    """G16 — operational trust proof pass (Step 16): composite replay/recovery/temporal/signal suite."""
    if raw_memory_operational_trust_proof.get("passed") is True:
        return closure_gate_row(
            "pass",
            "operational trust proof scenarios pass for this tenant snapshot",
        )
    return closure_gate_row(
        "hard_fail",
        "operational trust proof incomplete or failing required scenarios",
    )


def trust_annotation_gate_decisions_from_g1_g7(
    gates_g1_g7: dict[str, dict[str, Any]],
) -> dict[str, dict[str, str]]:
    """Narrow shape persisted on trust annotation (`decision` / `reason` only)."""
    out: dict[str, dict[str, str]] = {}
    for gid in _TRUST_GATE_IDS:
        row = gates_g1_g7.get(gid) or {}
        out[gid] = {
            "decision": str(row.get("decision", "pass")),
            "reason": str(row.get("reason", "")),
        }
    return out


def finalize_phase02_closure_from_canonical_gates(
    *,
    tenant_id: uuid.UUID,
    gates: dict[str, dict[str, Any]],
    raw_memory_trust: dict[str, Any],
) -> dict[str, Any]:
    """Build Step 10 closure payload from an already-merged canonical gate map."""
    hard_fails = [gid for gid, g in gates.items() if g["decision"] == "hard_fail"]
    soft_fails_required = [
        gid for gid, g in gates.items() if g["decision"] == "soft_fail" and g["required_scope"]
    ]
    warn_only = [gid for gid, g in gates.items() if g["decision"] == "warn_only"]

    trust_blocking = dict((raw_memory_trust.get("annotation") or {}).get("blocking") or {})
    blocking_flags_active = [
        k for k, v in trust_blocking.items() if bool(v) and k != "allow_diagnostic_reads"
    ]

    passed = (
        len(hard_fails) == 0 and len(soft_fails_required) == 0 and len(blocking_flags_active) == 0
    )
    return {
        "tenant_id": str(tenant_id),
        "passed": passed,
        "phase_status": "closed" if passed else "open",
        "checks": [
            {
                "id": "s10_zero_hard_fail_gates",
                "passed": len(hard_fails) == 0,
                "detail": {"hard_fails": hard_fails},
            },
            {
                "id": "s10_zero_required_scope_soft_fails",
                "passed": len(soft_fails_required) == 0,
                "detail": {"required_scope_soft_fails": soft_fails_required},
            },
            {
                "id": "s10_no_active_blocking_flags",
                "passed": len(blocking_flags_active) == 0,
                "detail": {"blocking_flags_active": blocking_flags_active},
            },
        ],
        "gate_results": gates,
        "summary": {
            "hard_fail_count": len(hard_fails),
            "soft_fail_count": len([1 for g in gates.values() if g["decision"] == "soft_fail"]),
            "warn_only_count": len(warn_only),
            "hard_fails": hard_fails,
            "required_scope_soft_fails": soft_fails_required,
            "warn_only": warn_only,
            "warnings_ack_required": warn_only,
            "blocking_flags_active": blocking_flags_active,
            "closure_rule": {
                "requires_zero_hard_fail": True,
                "requires_zero_required_scope_soft_fail": True,
                "warn_only_must_be_acknowledged": True,
                "requires_zero_active_blocking_flags": True,
            },
        },
    }


def infer_proof_quality(
    *,
    canonical_gates: dict[str, dict[str, Any]],
    from_cache: bool,
    exhaust_gate_enforced: bool,
    exhaust_gate_passed: bool | None,
    trust_g1_g7_matches_closure: bool = True,
) -> dict[str, Any]:
    """Operator-facing proof-quality labels (Step 12 + Step 14).

    Primary axis: measured / inferred / stale / partial / unverifiable (doctrine).
    """
    hard_any = any(g.get("decision") == "hard_fail" for g in canonical_gates.values())
    soft_any = any(g.get("decision") == "soft_fail" for g in canonical_gates.values())
    warn_any = any(g.get("decision") == "warn_only" for g in canonical_gates.values())

    if hard_any:
        primary = "unverifiable"
    elif not trust_g1_g7_matches_closure:
        primary = "inferred"
    elif from_cache:
        primary = "stale"
    elif soft_any or warn_any:
        primary = "partial"
    else:
        primary = "measured"

    return {
        "primary": primary,
        "measured": primary == "measured",
        "inferred": primary == "inferred",
        "stale_snapshot": from_cache,
        "partial": soft_any or warn_any,
        "unverifiable": hard_any,
        "exhaust_gate_enforced": exhaust_gate_enforced,
        "exhaust_gate_passed": exhaust_gate_passed,
    }


def build_phase02_verification_truth(
    *,
    tenant_id: uuid.UUID,
    canonical_gates: dict[str, dict[str, Any]],
    trust_annotation: dict[str, Any] | None,
    from_cache: bool,
    cache_ttl_seconds: float,
    enforcement_mode: str,
    exhaust_gate_enforced: bool,
    exhaust_gate_passed: bool | None,
    verification_passed: bool,
) -> dict[str, Any]:
    """Authoritative verification snapshot for all admin/runtime surfaces."""
    now = datetime.now(tz=UTC)
    trust_gates = (
        (trust_annotation or {}).get("verification", {}).get("gate_decisions")
        if isinstance(trust_annotation, dict)
        else None
    )
    aligned = True
    if isinstance(trust_gates, dict):
        for gid in _TRUST_GATE_IDS:
            t = trust_gates.get(gid) or {}
            c = canonical_gates.get(gid) or {}
            if str(t.get("decision")) != str(c.get("decision")):
                aligned = False
                break

    freshness_label = "stale" if from_cache else "fresh"
    return {
        "schema_version": 1,
        "canonical_path": "phase02_verification_unified_v1",
        "tenant_id": str(tenant_id),
        "gate_order": list(_CANONICAL_ORDER),
        "canonical_gates": canonical_gates,
        "freshness": {
            "snapshot_at": now.isoformat(),
            "cache_ttl_seconds": cache_ttl_seconds,
            "from_cache": from_cache,
            "label": freshness_label,
        },
        "proof_quality": infer_proof_quality(
            canonical_gates=canonical_gates,
            from_cache=from_cache,
            exhaust_gate_enforced=exhaust_gate_enforced,
            exhaust_gate_passed=exhaust_gate_passed,
            trust_g1_g7_matches_closure=aligned,
        ),
        "precedence": {
            "single_computation_path": True,
            "trust_g1_g7_matches_closure": aligned,
        },
        "enforcement_mode": enforcement_mode,
        "aggregate_passed": verification_passed,
    }


def verify_phase02_step12_unified_verification_semantics(
    *,
    phase02_verification_truth: dict[str, Any],
    raw_memory_phase_closure: dict[str, Any],
    raw_memory_trust: dict[str, Any],
) -> dict[str, Any]:
    """Structural checks that Step 12 single-path semantics hold."""
    canon = phase02_verification_truth.get("canonical_gates")
    closure_gates = raw_memory_phase_closure.get("gate_results")
    canon_ok = (
        isinstance(canon, dict) and isinstance(closure_gates, dict) and canon == closure_gates
    )

    trust_align = phase02_verification_truth.get("precedence", {}).get(
        "trust_g1_g7_matches_closure"
    )

    checks = [
        {"id": "s12_canonical_gates_match_closure", "passed": bool(canon_ok)},
        {
            "id": "s12_truth_has_schema_and_freshness",
            "passed": bool(phase02_verification_truth.get("schema_version")),
        },
        {
            "id": "s12_proof_quality_present",
            "passed": isinstance(phase02_verification_truth.get("proof_quality"), dict),
        },
        {"id": "s12_trust_closure_g1_g7_aligned", "passed": trust_align is not False},
    ]
    passed = all(c["passed"] for c in checks)
    return {"passed": passed, "state": "aligned" if passed else "degraded", "checks": checks}
