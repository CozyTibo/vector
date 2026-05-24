"""Phase S2.4 — TCRE causal_edge retrieval indexing."""

from __future__ import annotations

from vector.domains.cortex.retrieval.retrieval_tcre_binding import (
    DEFAULT_MAX_TCRE_CAUSAL_EDGES_PER_EPOCH_V1,
    max_tcre_causal_edges_per_epoch_v1,
    retrieval_index_tcre_causal_edges_enabled_v1,
)


def test_causal_edge_indexing_enabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CORTEX_RETRIEVAL_INDEX_TCRE_CAUSAL_EDGES", raising=False)
    assert retrieval_index_tcre_causal_edges_enabled_v1() is True


def test_causal_edge_indexing_disabled_via_env(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_RETRIEVAL_INDEX_TCRE_CAUSAL_EDGES", "0")
    assert retrieval_index_tcre_causal_edges_enabled_v1() is False


def test_max_causal_edges_per_epoch_bounded() -> None:
    assert max_tcre_causal_edges_per_epoch_v1(max_materializations=10) == 10
    assert (
        max_tcre_causal_edges_per_epoch_v1(max_materializations=10_000)
        == DEFAULT_MAX_TCRE_CAUSAL_EDGES_PER_EPOCH_V1
    )
