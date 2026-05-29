"""Linear issue_relation → graph kind mapping."""

from __future__ import annotations

from vector.domains.cortex.graph.linear_relations import relationship_kind_for_linear_relation


def test_blocks_and_duplicate_map_to_typed_kinds() -> None:
    assert relationship_kind_for_linear_relation("blocks") == (
        "blocks",
        "linear.issue_relation.blocks",
    )
    assert relationship_kind_for_linear_relation("duplicate") == (
        "duplicates",
        "linear.issue_relation.duplicates",
    )


def test_unknown_linear_relation_stays_relates_to() -> None:
    assert relationship_kind_for_linear_relation("related") == (
        "relates_to",
        "linear.issue_relation.related",
    )
    assert relationship_kind_for_linear_relation(None) == (
        "relates_to",
        "linear.issue_relation.related",
    )
