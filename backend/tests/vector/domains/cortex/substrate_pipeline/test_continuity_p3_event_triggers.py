"""Phase 3.2 — P2-B event triggers proof evaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from vector.domains.cortex.substrate_pipeline.continuity_p3_event_triggers import (
    evaluate_p3_2_event_triggers_proof_v1,
    verify_p2b_event_trigger_wiring_v1,
)


def test_static_wiring_ok() -> None:
    wiring = verify_p2b_event_trigger_wiring_v1()
    assert wiring["wiring_ok"] is True


def test_p3_2_pass_with_graph_hash_drive() -> None:
    wiring = verify_p2b_event_trigger_wiring_v1()
    snapshot = {
        "event_triggers_enabled": True,
        "wiring": wiring,
        "triggers": {
            "surface_kind": "execution_event_triggers",
            "graph_hash_trigger_registered": True,
            "live_graph_projection_stable_hash": "abc",
        },
        "execution_inspect_event_triggers": {"surface_kind": "execution_event_triggers"},
    }
    graph_drive = {
        "acquired": True,
        "graph_hash_trigger": {
            "hash_changed": True,
            "walk_schedule": {"scheduled": True},
            "walks_scheduled": True,
            "new_hash": "abc",
        },
    }
    proof = evaluate_p3_2_event_triggers_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        graph_hash_drive=graph_drive,
        deploy_recorded_at=datetime(2026, 5, 22, 12, 0, 0, tzinfo=UTC),
    )
    assert proof["p3_2_pass"] is True
    assert proof["verification"]["cleared_for_step_33"] is True
