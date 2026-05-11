"""Phase 02 Step 13 — replay divergence proof hardening (D0–D5 + forbidden denial paths)."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.ingestion.raw_memory_replay import (
    FORBIDDEN_DIVERGENCE_CLASSES,
    REPLAY_DIVERGENCE_CLASS_IDS,
    REPLAY_DIVERGENCE_CLASS_META,
)

_ORDER = {"D0": 0, "D1": 1, "D2": 2, "D3": 3, "D4": 4, "D5": 5}


def verify_phase02_step13_replay_divergence_hardening(
    raw_memory_replay: dict[str, Any],
) -> dict[str, Any]:
    """Structural proof that forbidden classes deny trusted replay completion.

    Matrix coverage (D0–D5 scenarios) is enforced by the Step 13 integration tests.
    """
    checks: list[dict[str, Any]] = []

    registry_ok = set(REPLAY_DIVERGENCE_CLASS_META.keys()) == set(REPLAY_DIVERGENCE_CLASS_IDS)
    checks.append(
        {
            "id": "s13_divergence_registry_d0_d5",
            "passed": registry_ok,
            "detail": {"classes": sorted(REPLAY_DIVERGENCE_CLASS_IDS)},
        }
    )

    forbidden_job_blocking = True
    _jobs_raw: Any = raw_memory_replay.get("jobs")
    jobs: list[Any] = list(_jobs_raw) if isinstance(_jobs_raw, list) else []
    for job in jobs:
        if not isinstance(job, dict):
            forbidden_job_blocking = False
            continue
        hi = str((job.get("highest_divergence") or {}).get("class", "D0"))
        blocking = bool(job.get("blocking"))
        if hi in FORBIDDEN_DIVERGENCE_CLASSES and not blocking:
            forbidden_job_blocking = False
            break

    checks.append(
        {
            "id": "s13_forbidden_class_requires_blocking_job",
            "passed": forbidden_job_blocking,
            "detail": {"jobs_examined": len(jobs)},
        }
    )

    summary_hi = str(
        (raw_memory_replay.get("summary") or {}).get("highest_divergence", {}).get("class", "D0")
    )
    agg_passed = raw_memory_replay.get("passed") is True
    forbidden_aggregate_denial = (
        summary_hi not in FORBIDDEN_DIVERGENCE_CLASSES or not agg_passed
    )
    checks.append(
        {
            "id": "s13_forbidden_aggregate_denial",
            "passed": forbidden_aggregate_denial,
            "detail": {
                "summary_highest": summary_hi,
                "aggregate_passed": agg_passed,
            },
        }
    )

    acceptable_without_blocking = True
    for job in jobs:
        if not isinstance(job, dict):
            acceptable_without_blocking = False
            continue
        hi = str((job.get("highest_divergence") or {}).get("class", "D0"))
        blocking = bool(job.get("blocking"))
        if hi in {"D0", "D1", "D2"} and blocking:
            acceptable_without_blocking = False
            break

    checks.append(
        {
            "id": "s13_acceptable_classes_non_blocking",
            "passed": acceptable_without_blocking,
            "detail": {"jobs_examined": len(jobs)},
        }
    )

    states_consistent = True
    state = str(raw_memory_replay.get("state", ""))
    if summary_hi in FORBIDDEN_DIVERGENCE_CLASSES:
        if state not in {"replay-diverged"}:
            states_consistent = False
    elif _ORDER.get(summary_hi, 0) <= _ORDER["D2"]:
        if summary_hi == "D0" and state not in {"replay-safe", "unverifiable", "partial"}:
            states_consistent = False
        elif summary_hi in {"D1", "D2"} and state not in {"partial", "unverifiable"}:
            states_consistent = False

    checks.append(
        {
            "id": "s13_replay_state_matches_summary_severity",
            "passed": states_consistent,
            "detail": {"state": state, "summary_highest": summary_hi},
        }
    )

    passed = all(bool(c.get("passed")) for c in checks)
    return {
        "passed": passed,
        "state": "hardened" if passed else "degraded",
        "checks": checks,
        "summary": {
            "forbidden_classes": sorted(FORBIDDEN_DIVERGENCE_CLASSES),
            "jobs_examined": len(jobs),
        },
    }
