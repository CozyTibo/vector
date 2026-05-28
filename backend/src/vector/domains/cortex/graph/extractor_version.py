"""Graph extractor version baseline."""

from __future__ import annotations

GRAPH_EXTRACTOR_VERSION = 1


def effective_graph_extractor_version(override: int | None = None) -> int:
    return max(GRAPH_EXTRACTOR_VERSION, int(override or 0))
