"""Operator-facing labels for pipeline overview phase strip and attention."""

from __future__ import annotations

import re
from typing import Any, Literal

OperatorPhase = Literal[
    "ingestion",
    "canonical",
    "identity",
    "graph",
    "reconstruction",
    "retrieval",
    "synthesis",
]
PhaseStatus = Literal["healthy", "running", "waiting", "blocked", "degraded"]

# Short text for phase cards (keep compact).
_STATUS_LABEL: dict[PhaseStatus, str] = {
    "healthy": "Healthy",
    "running": "Running",
    "waiting": "Waiting",
    "blocked": "Blocked",
    "degraded": "Has gaps",
}

# Longer hint only used in attention / optional tooltips.
_STATUS_HINT: dict[PhaseStatus, str] = {
    "healthy": "This step is in good shape; no operator action needed.",
    "running": "The execution engine is actively working on this step.",
    "waiting": "This step is idle until an earlier pipeline step finishes.",
    "blocked": "The pipeline cannot advance until this is resolved.",
    "degraded": "This step ran but has known gaps or quality issues.",
}

_OMISSION_COPY: dict[str, str] = {
    "canonical_backlog_unmaterialized": "{n} ingested rows are not canonicalized yet",
    "unsupported_payload": "{n} raw rows use unsupported payload shapes",
    "parse_failure": "{n} rows failed parsing during canonicalization",
    "schema_drift_detected": "{n} schema drift cases detected",
    "replay_conflicted_identity": "{n} identity replay conflict(s)",
    "unresolved_actor": "{n} unresolved identity ambiguities",
    "orphan_identity_cluster": "{n} orphan identity cluster(s)",
    "continuity_unverified": "{n} merge proposal(s) awaiting decision",
    "orphan_artifacts": "{n} graph node(s) without links",
    "pending_link_candidates": "{n} relationship candidate(s) not promoted",
    "orphan_disconnected_component": "{n} disconnected graph component(s)",
    "orphan_awaiting_promotion": "{n} orphan(s) waiting for link promotion",
    "orphan_identity_unresolved": "{n} graph orphan(s) tied to unresolved identity",
    "reconstruction_not_yet_run": "Reconstruction has not run yet for this tenant",
    "reconstruction_never_run": "Reconstruction has not run yet for this tenant",
    "retrieval_index_never_built": "Retrieval index has never been published",
    "retrieval_index_stale": "Published retrieval index is behind upstream epochs",
    "retrieval_upstream_tcre_gap": "Retrieval is waiting on reconstruction output",
    "retrieval_replay_divergence": "{n} retrieval replay divergence(s)",
    "ingestion_gap_detected": "{n} ingestion gap(s) affecting downstream steps",
    "graph_fake_green_blocked": "Graph metrics look healthy but traversal is blocked (anti-fake-green)",
    "fake_green_blocked": "Metrics look healthy but downstream work is blocked",
    "topology_wait": "Waiting on graph topology / walk substrate",
    "retrieval_retry_exhausted": "Retrieval retries exhausted — fix upstream then re-run",
    "fsm_blocked": "Execution is blocked",
}

_LEASE_BLOCK_COPY: dict[str, str] = {
    "topology_wait": "Execution is waiting for graph topology / walks to become ready",
    "retrieval_retry_exhausted": "Retrieval failed repeatedly — repair upstream data, then re-run from retrieval",
    "canonical_stall": "Canonical phase is stalled",
    "identity_stall": "Identity phase is stalled",
}


def _fmt_count(n: int | None, template: str) -> str:
    if n is None:
        return template.replace("{n}", "Some").replace("{n:,}", "Some")
    return template.replace("{n:,}", f"{n:,}").replace("{n}", str(n))


def _humanize_snake_key(key: str, count: int | None = None) -> str:
    k = key.strip().lower()
    if k in _OMISSION_COPY:
        return _fmt_count(count, _OMISSION_COPY[k])
    if k in _LEASE_BLOCK_COPY:
        return _LEASE_BLOCK_COPY[k]
    label = k.replace("_", " ").strip()
    if count is not None and count > 0:
        return f"{count:,} issue(s): {label}"
    return label.capitalize()


def humanize_blocker_line(line: str) -> str:
    """Turn a raw blocker / omission token into an operator sentence."""
    raw = (line or "").strip()
    if not raw:
        return ""
    if raw.lower().startswith("freshness="):
        return f"Identity data may be stale ({raw.split('=', 1)[-1]})"
    if raw.endswith(" substrate is critical"):
        return raw.replace(" substrate is critical", " is in a critical state")
    if raw.endswith(" has known gaps"):
        return raw.replace(" has known gaps", " completed with known gaps")
    m = re.match(r"^([a-z0-9_]+):\s*(\d+)$", raw, re.IGNORECASE)
    if m:
        return _humanize_snake_key(m.group(1), int(m.group(2)))
    if re.match(r"^\d+\s+schema_drift case\(s\)$", raw, re.IGNORECASE):
        n = int(raw.split()[0])
        return f"{n:,} canonical schema drift case(s)"
    if raw.startswith("last_replay_divergence_at="):
        return "Last reconstruction replay did not match stored output"
    return _humanize_snake_key(raw)


def phase_status_label(status: PhaseStatus) -> str:
    return _STATUS_LABEL.get(status, status.replace("_", " ").title())


def phase_display_label_v1(
    *,
    status: PhaseStatus,
    substrate_phase_outcome: str | None = None,
) -> str:
    """Wave S5: show substrate receipt outcomes verbatim (e.g. phase 03 COMPLETED_EMPTY)."""
    outcome = (substrate_phase_outcome or "").strip().upper()
    if outcome == "COMPLETED_EMPTY":
        return "COMPLETED_EMPTY"
    return phase_status_label(status)


def phase_status_hint(status: PhaseStatus) -> str:
    return _STATUS_HINT.get(status, "")


def humanize_phase_issues(
    *,
    operator_phase: OperatorPhase,
    status: PhaseStatus,
    blockers: list[str],
    backlog_count: int | None,
) -> list[str]:
    """Full sentences for the Attention list (not shown on phase cards)."""
    issues: list[str] = []
    for b in blockers:
        msg = humanize_blocker_line(b)
        if msg and msg not in issues:
            issues.append(msg)
    if status == "waiting" and backlog_count and backlog_count > 0 and not issues:
        issues.append(
            f"{backlog_count:,} items are queued; this step will run when the execution engine reaches it"
        )
    if status == "degraded" and not issues:
        issues.append("Completed with known gaps — open the phase page for detail")
    if status == "blocked" and not issues:
        issues.append("Cannot proceed until upstream work completes or blockers are cleared")
    return issues[:6]


def build_attention_lines(
    phases: list[dict[str, Any]],
    *,
    execution_block_reason: str | None,
) -> list[str]:
    lines: list[str] = []
    if execution_block_reason and execution_block_reason.strip():
        lines.append(humanize_blocker_line(execution_block_reason.strip()))
    for p in phases:
        phase_label = str(p.get("phase", "")).replace("_", " ").title()
        status = str(p.get("status", ""))
        if status not in ("blocked", "degraded", "waiting"):
            continue
        issues = list(p.get("issues") or [])
        if not issues:
            hint = phase_status_hint(status)  # type: ignore[arg-type]
            if hint:
                lines.append(f"{phase_label}: {hint}")
            continue
        for issue in issues[:3]:
            lines.append(f"{phase_label}: {issue}")
    return lines[:8]


def object_count_label(count: int | None) -> str | None:
    if count is None:
        return None
    return f"{count:,} objects"
