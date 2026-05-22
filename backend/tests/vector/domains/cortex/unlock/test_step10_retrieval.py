"""Step 10 A6 validation helpers."""

from __future__ import annotations

from vector.domains.cortex.retrieval.retrieval_skip_registry import RET_SKIP_GRAPH_DISCONNECTED_V1
from vector.domains.cortex.unlock.step10_retrieval import (
    evaluate_a6_evidence_recovery_v1,
    is_graph_disconnect_dominated_v1,
    summarize_ret_skip_codes_v1,
)


def test_graph_disconnect_dominated_only_when_all_graph_skips() -> None:
    assert is_graph_disconnect_dominated_v1({RET_SKIP_GRAPH_DISCONNECTED_V1: 3}) is True
    assert (
        is_graph_disconnect_dominated_v1(
            {RET_SKIP_GRAPH_DISCONNECTED_V1: 1, "RET-SKIP-WALK-INCOMPLETE": 1}
        )
        is False
    )


def test_summarize_ret_skip_codes() -> None:
    counts = summarize_ret_skip_codes_v1(
        [{"source": "walk", "code": "walk_incomplete"}],
    )
    assert "RET-SKIP-WALK-INCOMPLETE" in counts


def test_a6_passes_with_materialized_entries() -> None:
    ok, detail = evaluate_a6_evidence_recovery_v1(
        entries_materialized=12,
        skip_code_counts={RET_SKIP_GRAPH_DISCONNECTED_V1: 5},
    )
    assert ok is True
    assert "entries_materialized=12" in detail


def test_a6_fails_when_graph_disconnect_dominated_and_empty() -> None:
    ok, detail = evaluate_a6_evidence_recovery_v1(
        entries_materialized=0,
        skip_code_counts={RET_SKIP_GRAPH_DISCONNECTED_V1: 4},
    )
    assert ok is False
    assert RET_SKIP_GRAPH_DISCONNECTED_V1 in detail
