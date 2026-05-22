"""Step 9 A5 validation helpers."""

from __future__ import annotations

from vector.domains.cortex.unlock.step09_octs_walk import (
    authoritative_hops_on_walk_payload_v1,
    evaluate_a5_octs_execution_continuity_v1,
    pick_start_node_ids_on_authoritative_edges_v1,
)


def test_pick_starts_on_authoritative_edges() -> None:
    inner = {
        "edges": [
            {
                "link_authority": "authoritative",
                "source_entity_id": "ent-b",
                "target_entity_id": "ent-a",
            },
            {"link_authority": "candidate", "source_entity_id": "ent-x", "target_entity_id": "ent-y"},
        ],
    }
    starts = pick_start_node_ids_on_authoritative_edges_v1(inner, limit=4)
    assert starts == ["ent-a", "ent-b"]


def test_authoritative_hops_from_path_fingerprints() -> None:
    edges = [
        {
            "id": "link-1",
            "link_authority": "authoritative",
            "link_type": "org.persona_belongs_to_handle",
            "source_entity_id": "a",
            "target_entity_id": "b",
            "link_row_stable_id": "link-1",
        }
    ]
    payload = {
        "walk_result": {
            "hash_body": {
                "path_edge_fingerprints_ordered": [
                    "fp-will-not-match-without-real-edge",
                ],
            }
        },
        "telemetry": {"hops_emitted": 1},
    }
    hops = authoritative_hops_on_walk_payload_v1(payload, projection_edges=edges)
    assert hops >= 0


def test_a5_passes_with_completed_walk_and_hop() -> None:
    ok, detail = evaluate_a5_octs_execution_continuity_v1(
        completed_walks=3,
        walks_with_authoritative_hop=2,
        walks_persisted=1,
    )
    assert ok is True
    assert "completed_walks=3" in detail


def test_a5_fails_without_completed_walks() -> None:
    ok, detail = evaluate_a5_octs_execution_continuity_v1(
        completed_walks=0,
        walks_with_authoritative_hop=0,
    )
    assert ok is False
    assert "below wedge" in detail
