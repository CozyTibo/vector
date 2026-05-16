"""Artifact lineage edge id stability."""

from __future__ import annotations

from vector.domains.cortex.lineage.artifact_lineage_graph import lineage_edge_id_v1


def test_lineage_edge_id_deterministic() -> None:
    a = lineage_edge_id_v1(
        from_kind="raw_event",
        from_ref="r1",
        to_kind="canonical_artifact",
        to_ref="c1",
        edge_kind="materialized_from",
    )
    b = lineage_edge_id_v1(
        from_kind="raw_event",
        from_ref="r1",
        to_kind="canonical_artifact",
        to_ref="c1",
        edge_kind="materialized_from",
    )
    assert a == b
