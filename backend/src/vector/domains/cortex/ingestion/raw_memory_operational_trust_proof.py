"""Phase 02 Step 16 — operational trust proof pass (composite operational scenarios)."""

from __future__ import annotations

from typing import Any


def _freshness_labels_coherent(phase02_verification_truth: dict[str, Any]) -> bool:
    """Stale snapshot must report stale; live computation must report fresh."""
    fr_raw = phase02_verification_truth.get("freshness")
    if not isinstance(fr_raw, dict):
        return False
    from_cache = fr_raw.get("from_cache")
    label = fr_raw.get("label")
    if from_cache is True:
        return label == "stale"
    if from_cache is False:
        return label == "fresh"
    return False


def verify_phase02_step16_operational_trust_proof(
    *,
    runtime_correctness: dict[str, Any],
    raw_memory_temporal: dict[str, Any],
    raw_memory_replay: dict[str, Any],
    raw_memory_replay_hardening: dict[str, Any],
    raw_memory_failure_recovery: dict[str, Any],
    raw_memory_critical_integrity: dict[str, Any],
    raw_memory_trust_signal: dict[str, Any],
    phase02_verification_truth: dict[str, Any],
) -> dict[str, Any]:
    """Scenario bundle for G16 — aggregates stabilization pillars into an operational proof surface.

    Uses existing tenant verification artifacts (no synthetic mutation): replay/divergence depth,
    corruption/recovery paths, temporal ordering, trust signals + freshness coherence, and
    reconstruction-critical pointer integrity.
    """
    checks: list[dict[str, Any]] = []

    replay_ok = bool(raw_memory_replay.get("passed")) and bool(raw_memory_replay_hardening.get("passed"))
    checks.append(
        {
            "id": "s16_replay_and_denial_paths",
            "passed": replay_ok,
            "detail": {
                "replay_state": raw_memory_replay.get("state"),
                "replay_hardening_state": raw_memory_replay_hardening.get("state"),
            },
        }
    )

    corruption_recovery_ok = bool(raw_memory_failure_recovery.get("passed")) and bool(
        runtime_correctness.get("passed")
    )
    checks.append(
        {
            "id": "s16_corruption_recovery_and_runtime_correctness",
            "passed": corruption_recovery_ok,
            "detail": {
                "failure_recovery_state": raw_memory_failure_recovery.get("state"),
                "runtime_correctness_state": runtime_correctness.get("state"),
            },
        }
    )

    temporal_ok = bool(raw_memory_temporal.get("passed"))
    checks.append(
        {
            "id": "s16_temporal_ordering_and_continuity",
            "passed": temporal_ok,
            "detail": raw_memory_temporal.get("state"),
        }
    )

    integrity_ok = bool(raw_memory_critical_integrity.get("passed"))
    checks.append(
        {
            "id": "s16_reconstruction_critical_pointers",
            "passed": integrity_ok,
            "detail": raw_memory_critical_integrity.get("state"),
        }
    )

    signal_ok = bool(raw_memory_trust_signal.get("passed"))
    checks.append(
        {
            "id": "s16_trust_signal_operator_surface",
            "passed": signal_ok,
            "detail": raw_memory_trust_signal.get("state"),
        }
    )

    fresh_ok = _freshness_labels_coherent(phase02_verification_truth)
    checks.append(
        {
            "id": "s16_verification_truth_freshness_coherence",
            "passed": fresh_ok,
            "detail": phase02_verification_truth.get("freshness"),
        }
    )

    replay_summary = raw_memory_replay.get("summary") if isinstance(raw_memory_replay.get("summary"), dict) else {}
    hard_sum = (
        raw_memory_replay_hardening.get("summary")
        if isinstance(raw_memory_replay_hardening.get("summary"), dict)
        else {}
    )
    proof_artifacts_ok = (
        "jobs_examined" in replay_summary
        and "jobs_examined" in hard_sum
        and "forbidden_classes" in hard_sum
    )
    checks.append(
        {
            "id": "s16_replay_proof_artifacts_present",
            "passed": proof_artifacts_ok,
            "detail": {"replay_summary_keys": list(replay_summary.keys()), "hardening_summary": hard_sum},
        }
    )

    passed = all(bool(c.get("passed")) for c in checks)
    return {
        "passed": passed,
        "state": "operationally_proven" if passed else "proof_incomplete",
        "checks": checks,
        "summary": {
            "scenarios_total": len(checks),
            "scenarios_passed": sum(1 for c in checks if c.get("passed")),
        },
    }
