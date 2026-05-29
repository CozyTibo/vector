"""Unit tests for graph admin stats helpers."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from vector.domains.cortex.graph.admin import graph_stats_by_kind
from vector.domains.cortex.graph.relationship_kinds import EXTRACTABLE_RELATIONSHIP_KINDS


def test_graph_stats_by_kind_includes_all_extractable_kinds_at_zero() -> None:
    session = MagicMock()
    session.execute.return_value.all.return_value = []
    tenant_id = uuid.uuid4()

    stats = graph_stats_by_kind(session, tenant_id)

    assert [row["relationship_kind"] for row in stats] == list(EXTRACTABLE_RELATIONSHIP_KINDS)
    assert all(row["count"] == 0 for row in stats)
    assert stats[0]["relationship_kind_label"] == "Authored by"


def test_graph_stats_by_kind_merges_db_counts() -> None:
    session = MagicMock()
    session.execute.return_value.all.return_value = [
        ("mentions", 12),
        ("authored_by", 3),
    ]
    tenant_id = uuid.uuid4()

    stats = graph_stats_by_kind(session, tenant_id)
    by_kind = {row["relationship_kind"]: row["count"] for row in stats}

    assert by_kind["mentions"] == 12
    assert by_kind["authored_by"] == 3
    assert by_kind["references"] == 0
    assert by_kind["replies_to"] == 0
