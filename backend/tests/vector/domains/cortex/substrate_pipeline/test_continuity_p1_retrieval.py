"""Phase 1 step 1.6 — P1-C retrieval island proof evaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from vector.domains.cortex.retrieval.retrieval_component_materialization import (
    RETRIEVAL_PROPAGATION_MODE_COMPONENT_V1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p1_retrieval import (
    evaluate_p1_6_retrieval_proof_v1,
)


def _proof_snapshot() -> dict:
    return {
        "component_scope": {
            "component_scope_enabled": True,
            "min_component_entities": 2,
            "island_entity_count": 120,
            "island_meta": {"islands_eligible_count": 2, "island_scope_id": "scope-abc"},
        },
        "materialization_stats": {
            "retrieval_propagation_mode": RETRIEVAL_PROPAGATION_MODE_COMPONENT_V1,
            "largest_island_selected": True,
            "islands_eligible_count": 2,
            "island_entity_count": 120,
            "outside_island_scope_entity_count": 40,
            "island_scope_id": "scope-abc",
            "build_state": "PUBLISHED",
            "ok": True,
            "entries_materialized": 15,
        },
        "aa4_footprint": {
            "total_entries": 42,
            "distinct_created_hours": 3,
        },
        "island_scope_id": "scope-abc",
    }


def test_p1_6_pass_when_component_retrieval_and_aa4() -> None:
    proof = evaluate_p1_6_retrieval_proof_v1(
        closure_git_sha="abc" * 10,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        proof_snapshot=_proof_snapshot(),
        deploy_recorded_at=datetime(2026, 5, 22, 23, 0, 0, tzinfo=UTC),
    )
    assert proof["p1_6_pass"] is True
    assert proof["verification"]["step_16_pass"] is True
    assert proof["verification"]["cleared_for_phase_2"] is True


def test_p1_6_fails_without_entries_materialized() -> None:
    snap = _proof_snapshot()
    snap["materialization_stats"]["entries_materialized"] = 0
    snap["aa4_footprint"]["total_entries"] = 0
    proof = evaluate_p1_6_retrieval_proof_v1(
        closure_git_sha="abc" * 10,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        proof_snapshot=snap,
    )
    assert proof["p1_6_pass"] is False


def test_p1_6_trace_only_skips_deploy_check() -> None:
    proof = evaluate_p1_6_retrieval_proof_v1(
        closure_git_sha="abc" * 10,
        prod_deploy={"verification": {"deploy_matches_closure_sha": False}},
        proof_snapshot=_proof_snapshot(),
        trace_only=True,
    )
    assert proof["checks"]["ecs_deploy_matches_closure_sha"] is True
