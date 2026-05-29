"""Registry tests for graph relationship kinds."""

from __future__ import annotations

from vector.domains.cortex.graph.relationship_kinds import (
    EXTRACTABLE_RELATIONSHIP_KINDS,
    label_for_kind,
)


def test_extractable_kinds_include_cross_tool_and_thread_edges() -> None:
    assert "references" in EXTRACTABLE_RELATIONSHIP_KINDS
    assert "replies_to" in EXTRACTABLE_RELATIONSHIP_KINDS
    assert "mentions" in EXTRACTABLE_RELATIONSHIP_KINDS
    assert "authored_by" in EXTRACTABLE_RELATIONSHIP_KINDS


def test_label_for_kind_known_and_unknown() -> None:
    assert label_for_kind("replies_to") == "Replies to"
    assert label_for_kind("custom_edge") == "Custom Edge"
