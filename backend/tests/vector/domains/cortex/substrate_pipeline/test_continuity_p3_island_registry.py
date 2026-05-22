"""Phase 3.1 — P2-C island registry proof evaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from vector.domains.cortex.substrate_pipeline.continuity_p3_island_registry import (
    evaluate_p3_1_island_registry_proof_v1,
)


def _snapshot(*, island_count: int = 2) -> dict:
    islands = [
        {
            "island_scope_id": f"scope{i:04x}",
            "entity_count": 10 + i,
            "authoritative_edge_count": 5 + i,
            "entity_ids": [f"00000000-0000-0000-0000-{i:012d}"],
            "last_walk_at": "2026-05-22T12:00:00+00:00",
            "last_retrieval_epoch": "epoch-a",
        }
        for i in range(island_count)
    ]
    return {
        "registry_enabled": True,
        "registry": {
            "surface_kind": "execution_island_registry",
            "component_schedule_enabled": True,
            "traversal_propagation": {
                "islands_eligible_count": island_count,
                "traversal_propagation_mode": "component",
            },
            "sync": {"synced": True, "island_count": island_count},
            "island_count": island_count,
            "islands": islands,
        },
        "execution_inspect_island_registry": {
            "surface_kind": "execution_island_registry",
            "island_count": island_count,
        },
    }


def test_p3_1_pass_with_persisted_islands() -> None:
    proof = evaluate_p3_1_island_registry_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=_snapshot(island_count=2),
        deploy_recorded_at=datetime(2026, 5, 22, 12, 0, 0, tzinfo=UTC),
    )
    assert proof["p3_1_pass"] is True
    assert proof["verification"]["cleared_for_step_32"] is True


def test_p3_1_fails_without_registry_rows() -> None:
    snap = _snapshot(island_count=0)
    snap["registry"]["traversal_propagation"]["islands_eligible_count"] = 2
    snap["registry"]["sync"]["synced"] = True
    proof = evaluate_p3_1_island_registry_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snap,
    )
    assert proof["p3_1_pass"] is False
