"""Phase B step B6 — fresh pipeline run proof evaluator."""

from __future__ import annotations

from vector.domains.cortex.substrate_pipeline.continuity_p0_post_ingestion_fresh_pipeline_run import (
    evaluate_p0_b6_post_ingestion_fresh_pipeline_run_proof_v1,
    verify_b6_post_ingestion_fresh_pipeline_run_wiring_v1,
)


def test_b6_wiring_static() -> None:
    assert verify_b6_post_ingestion_fresh_pipeline_run_wiring_v1()["wiring_ok"] is True


def test_b6_pass_with_fresh_run_evidence() -> None:
    snapshot = {
        "fresh_runs_in_window": 1,
        "fresh_run_evidence": [{"pipeline_run_id": "pr-new", "fresh_phases_ok": True}],
        "post_ingestion_fresh_run_schema_version": 1,
        "wiring": {"wiring_ok": True, "fresh_run_on_graph_change_enabled": True},
    }
    proof = evaluate_p0_b6_post_ingestion_fresh_pipeline_run_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        trace_only=False,
    )
    assert proof["p0_b6_pass"] is True
    assert proof["verification"]["cleared_for_phase_c"] is True


def test_b6_pass_when_drive_started() -> None:
    snapshot = {
        "fresh_runs_in_window": 0,
        "post_ingestion_fresh_run_schema_version": 1,
        "latest_pipeline_run_id": "pr-old",
        "wiring": {"wiring_ok": True, "fresh_run_on_graph_change_enabled": True},
    }
    drive = {
        "started": True,
        "fresh_pipeline_run_id": "pr-new",
        "prior_pipeline_run_id": "pr-old",
        "phase_started_at": {
            "phase_03_identity": "2026-05-23T00:00:00+00:00",
            "phase_04_graph": "2026-05-23T00:01:00+00:00",
            "phase_05_traversal": "2026-05-23T00:02:00+00:00",
        },
    }
    proof = evaluate_p0_b6_post_ingestion_fresh_pipeline_run_proof_v1(
        closure_git_sha="b" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        graph_drive=drive,
        trace_only=False,
    )
    assert proof["p0_b6_pass"] is True
