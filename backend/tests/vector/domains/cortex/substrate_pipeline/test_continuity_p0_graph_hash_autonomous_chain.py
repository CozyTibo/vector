"""Phase B step B5 — graph-hash autonomous chain proof evaluator."""

from __future__ import annotations

from vector.domains.cortex.substrate_pipeline.continuity_p0_graph_hash_autonomous_chain import (
    evaluate_p0_b5_graph_hash_autonomous_chain_proof_v1,
    verify_b5_graph_hash_autonomous_chain_wiring_v1,
)


def test_b5_wiring_static() -> None:
    assert verify_b5_graph_hash_autonomous_chain_wiring_v1()["wiring_ok"] is True


def test_b5_pass_with_chain_evidence() -> None:
    snapshot = {
        "complete_chains_in_window": 1,
        "latest_complete_chain": {"chain_ok": True, "pipeline_run_id": "pr-1"},
        "autonomous_chain_schema_version": 1,
        "event_triggers_inspect": {
            "graph_hash_trigger_registered": True,
            "event_triggers_enabled": True,
        },
        "wiring": {"wiring_ok": True},
    }
    proof = evaluate_p0_b5_graph_hash_autonomous_chain_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        trace_only=False,
    )
    assert proof["p0_b5_pass"] is True
    assert proof["verification"]["cleared_for_b6"] is True


def test_b5_pass_when_drive_ok() -> None:
    snapshot = {
        "complete_chains_in_window": 0,
        "autonomous_chain_schema_version": 1,
        "event_triggers_inspect": {
            "graph_hash_trigger_registered": True,
            "event_triggers_enabled": True,
        },
        "wiring": {"wiring_ok": True},
    }
    drive = {
        "chain_ok": True,
        "chain_links": {
            "retrieval": {"ok": True, "published_index_epoch": "epoch-x"},
        },
    }
    proof = evaluate_p0_b5_graph_hash_autonomous_chain_proof_v1(
        closure_git_sha="b" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        chain_drive=drive,
        trace_only=False,
    )
    assert proof["p0_b5_pass"] is True
