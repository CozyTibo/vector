"""Phase 3.3 — P2-D per-island synthesis proof evaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from vector.domains.cortex.synthesis.synthesis_per_island import GLOBAL_DEGRADATION_BRIEF_SURFACE_V1
from vector.domains.cortex.substrate_pipeline.continuity_p3_per_island_synthesis import (
    evaluate_p3_3_per_island_synthesis_proof_v1,
    verify_p2d_per_island_synthesis_wiring_v1,
)


def test_static_wiring_ok() -> None:
    wiring = verify_p2d_per_island_synthesis_wiring_v1()
    assert wiring["wiring_ok"] is True


def test_p3_3_pass_with_synthesis_drive() -> None:
    wiring = verify_p2d_per_island_synthesis_wiring_v1()
    snapshot = {
        "per_island_enabled": True,
        "wiring": wiring,
        "panel": {
            "surface_kind": "per_island_synthesis",
            "published_index_epoch": "epoch-abc",
            "island_count": 2,
            "outside_island_scope_entity_count": 7000,
            "islands": [{"island_scope_id": "a", "entity_count": 257}],
        },
        "execution_inspect_per_island_synthesis": {"surface_kind": "per_island_synthesis"},
    }
    synthesis_drive = {
        "acquired": True,
        "materialize_output": {
            "per_island_mode": True,
            "global_degradation_brief": {
                "surface_kind": GLOBAL_DEGRADATION_BRIEF_SURFACE_V1,
                "islands_synthesized_count": 1,
            },
            "island_results": [{"island_scope_id": "a", "jobs_completed": 1}],
            "jobs_completed": 1,
        },
    }
    proof = evaluate_p3_3_per_island_synthesis_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        synthesis_drive=synthesis_drive,
        deploy_recorded_at=datetime(2026, 5, 22, 12, 0, 0, tzinfo=UTC),
    )
    assert proof["p3_3_pass"] is True
    assert proof["verification"]["cleared_for_step_34"] is True
