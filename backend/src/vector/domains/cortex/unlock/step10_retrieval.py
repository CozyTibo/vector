"""War-room step 10 — evidence recovery / retrieval materialization (alive criterion A6)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from vector.domains.cortex.retrieval.retrieval_skip_registry import (
    RET_SKIP_GRAPH_DISCONNECTED_V1,
    normalize_skip_reasons_from_stats_v1,
)

A6_WEDGE_MIN_EVIDENCE_ATTEMPTS = 1
A6_WEDGE_MIN_ENTRIES_MATERIALIZED = 1


def summarize_ret_skip_codes_v1(skip_reasons: list[dict[str, Any]]) -> dict[str, int]:
    """Count normalized RET-SKIP codes from materialization stats or report rows."""
    normalized = normalize_skip_reasons_from_stats_v1(
        [r for r in skip_reasons if isinstance(r, dict)]
    )
    counts: Counter[str] = Counter()
    for row in normalized:
        code = str(row.get("ret_skip_code") or "").strip()
        if code:
            counts[code] += 1
    return dict(counts)


def is_graph_disconnect_dominated_v1(skip_code_counts: dict[str, int]) -> bool:
    """True when every recorded skip is RET-SKIP-GRAPH-DISCONNECTED (and at least one skip)."""
    if not skip_code_counts:
        return False
    non_graph = {k: v for k, v in skip_code_counts.items() if k != RET_SKIP_GRAPH_DISCONNECTED_V1}
    return not non_graph and skip_code_counts.get(RET_SKIP_GRAPH_DISCONNECTED_V1, 0) > 0


def evaluate_a6_evidence_recovery_v1(
    *,
    entries_materialized: int,
    skip_code_counts: dict[str, int],
    materialization_attempts: int = 1,
    accepted_rows: int | None = None,
) -> tuple[bool, str]:
    """Return (passed, detail) for alive criterion A6 after retrieval wedge."""
    entries = int(entries_materialized)
    accepted = int(accepted_rows) if accepted_rows is not None else entries
    attempts = int(materialization_attempts)
    dominated = is_graph_disconnect_dominated_v1(skip_code_counts)

    if entries >= A6_WEDGE_MIN_ENTRIES_MATERIALIZED or accepted >= A6_WEDGE_MIN_ENTRIES_MATERIALIZED:
        return (
            True,
            f"entries_materialized={entries}:accepted_rows={accepted}",
        )
    if attempts >= A6_WEDGE_MIN_EVIDENCE_ATTEMPTS and not dominated:
        top = max(skip_code_counts.items(), key=lambda kv: kv[1]) if skip_code_counts else None
        return (
            True,
            f"materialization_attempts={attempts}:not_graph_disconnect_dominated:top_skip={top}",
        )
    if dominated:
        return (
            False,
            f"dominated_by_{RET_SKIP_GRAPH_DISCONNECTED_V1}:skip_counts={skip_code_counts}",
        )
    if attempts < A6_WEDGE_MIN_EVIDENCE_ATTEMPTS:
        return False, f"materialization_attempts={attempts} below wedge minimum"
    return False, f"entries_materialized={entries}:skip_counts={skip_code_counts}"
