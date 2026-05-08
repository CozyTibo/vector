"""Phase 02 Step 11 — progressive trust enforcement readiness."""

from __future__ import annotations

from typing import Any, Literal

EnforcementMode = Literal["observe", "progressive", "strict"]
EnforcementOperation = Literal[
    "memory_query",
    "replay_trigger",
    "reconstruction_read",
    "retention_apply",
    "recovery_validate",
]

_HEALTHY = {"healthy", "replay-safe", "reconstruction-safe"}
_DEGRADED = {"partial", "degraded"}
_UNSAFE = {"lineage-incomplete"}
_CATASTROPHIC = {"corrupted", "continuity-broken", "replay-diverged"}


def _risk_tier(trust_state: str) -> str:
    if trust_state in _CATASTROPHIC:
        return "catastrophic"
    if trust_state in _UNSAFE:
        return "unsafe"
    if trust_state == "unverifiable":
        return "unverifiable"
    if trust_state in _DEGRADED:
        return "degraded"
    if trust_state in _HEALTHY:
        return "healthy"
    return "unknown"


def evaluate_progressive_enforcement(
    *,
    trust_annotation: dict[str, Any] | None,
    phase_closure: dict[str, Any] | None,
    mode: EnforcementMode,
    operation: EnforcementOperation,
) -> dict[str, Any]:
    annotation = trust_annotation or {}
    closure = phase_closure or {}
    trust_state = str(annotation.get("trust_state", "unverifiable"))
    tier = _risk_tier(trust_state)
    reason_codes = list(annotation.get("state_reason_codes", []))
    hard_fails = list((closure.get("summary") or {}).get("hard_fails", []))

    blocked = False
    would_block = False
    escalation = "allow"
    if mode == "strict":
        blocked = tier in {"catastrophic", "unsafe", "unverifiable"}
        would_block = blocked
        escalation = "blocked" if blocked else "allow"
    elif mode == "progressive":
        blocked = tier == "catastrophic"
        would_block = blocked or tier in {"unsafe", "unverifiable"}
        escalation = (
            "blocked"
            if blocked
            else ("warn" if would_block or tier == "degraded" else "allow")
        )
    else:  # observe
        blocked = False
        would_block = tier in {"catastrophic", "unsafe", "unverifiable"}
        escalation = "warn" if would_block or tier == "degraded" else "allow"

    if operation == "retention_apply" and tier in {"unsafe", "unverifiable"} and mode != "strict":
        # Strong warning for data-destructive-adjacent operation in calibration mode.
        would_block = True
        if not blocked:
            escalation = "warn"

    if (
        operation == "replay_trigger"
        and tier in {"unsafe", "unverifiable"}
        and mode == "progressive"
    ):
        would_block = True

    return {
        "operation": operation,
        "mode": mode,
        "trust_state": trust_state,
        "risk_tier": tier,
        "allowed": not blocked,
        "blocked": blocked,
        "would_block": would_block,
        "escalation": escalation,
        "reason_codes": reason_codes,
        "hard_fail_gates": hard_fails,
    }


def build_enforcement_summary(
    *,
    trust_annotation: dict[str, Any] | None,
    phase_closure: dict[str, Any] | None,
    mode: EnforcementMode,
) -> dict[str, Any]:
    operations: tuple[EnforcementOperation, ...] = (
        "memory_query",
        "replay_trigger",
        "reconstruction_read",
        "retention_apply",
        "recovery_validate",
    )
    decisions = {
        op: evaluate_progressive_enforcement(
            trust_annotation=trust_annotation,
            phase_closure=phase_closure,
            mode=mode,
            operation=op,
        )
        for op in operations
    }
    blocked = [op for op, d in decisions.items() if d["blocked"]]
    would_block = [op for op, d in decisions.items() if d["would_block"]]
    return {
        "mode": mode,
        "catastrophic_only_blocking": mode == "progressive",
        "decisions": decisions,
        "blocked_operations": blocked,
        "would_block_operations": would_block,
        "enforcement_readiness": {
            "has_block_paths": True,
            "has_simulated_non_block_paths": True,
            "ready_for_strict": len(would_block) == 0 and len(blocked) == 0,
        },
    }


def verify_phase02_step11_progressive_enforcement(
    *,
    trust_annotation: dict[str, Any] | None,
    phase_closure: dict[str, Any] | None,
    enforcement_mode: EnforcementMode,
) -> dict[str, Any]:
    one = build_enforcement_summary(
        trust_annotation=trust_annotation,
        phase_closure=phase_closure,
        mode=enforcement_mode,
    )
    two = build_enforcement_summary(
        trust_annotation=trust_annotation,
        phase_closure=phase_closure,
        mode=enforcement_mode,
    )
    deterministic = one == two
    mode_supported = enforcement_mode in {"observe", "progressive", "strict"}
    has_decisions = isinstance(one.get("decisions"), dict) and len(one["decisions"]) >= 5
    progressive_rule_ok = True
    if enforcement_mode == "progressive":
        for d in one["decisions"].values():
            if d["blocked"] and d["risk_tier"] != "catastrophic":
                progressive_rule_ok = False
                break
    checks = [
        {"id": "s11_enforcement_mode_supported", "passed": mode_supported},
        {"id": "s11_operation_decisions_present", "passed": has_decisions},
        {"id": "s11_progressive_catastrophic_only_blocking", "passed": progressive_rule_ok},
        {"id": "s11_deterministic_enforcement_decisions", "passed": deterministic},
    ]
    passed = all(c["passed"] for c in checks)
    return {
        "passed": passed,
        "state": "ready" if passed else "degraded",
        "checks": checks,
        "summary": one,
    }
