"""Phase 2.2 — continuity proof panel AA1–AA7."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
    AA_GATE_IDS_V1,
    build_continuity_proof_panel_v1,
    evaluate_aa7_no_wedge_scripts_v1,
    evaluate_p2_2_proof_panel_proof_v1,
    format_continuity_proof_panel_text_v1,
)


def test_aa7_fails_when_wedge_in_ops_log() -> None:
    gate = evaluate_aa7_no_wedge_scripts_v1(ops_log_text="ran unlock_step12_track_b_p3.py")
    assert gate["verdict"] == "FAIL"
    assert "unlock_step12" in str(gate["evidence"]["wedge_hits"])


def test_aa7_pass_with_wedge_free_ack() -> None:
    gate = evaluate_aa7_no_wedge_scripts_v1(ops_log_text=None, wedge_free_ack=True)
    assert gate["verdict"] == "PASS"


def test_format_panel_includes_all_aa_labels() -> None:
    panel = {
        "tenant_id": str(uuid.uuid4()),
        "pipeline_run_id": None,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "window_hours": 24,
        "gate_order": list(AA_GATE_IDS_V1),
        "gates": {
            gid: {
                "gate_id": gid,
                "verdict": "PASS",
                "criterion": "test",
                "detail": "ok",
            }
            for gid in AA_GATE_IDS_V1
        },
        "summary": {
            "pass_count": 7,
            "fail_count": 0,
            "advisory_count": 0,
            "total_gates": 7,
            "m3_autonomously_alive": True,
        },
    }
    text = format_continuity_proof_panel_text_v1(panel)
    for gid in AA_GATE_IDS_V1:
        assert gid in text
    assert "Summary:" in text
    assert "M3 autonomously alive: YES" in text


def test_build_panel_evaluates_all_gates() -> None:
    tenant_id = uuid.uuid4()
    session = MagicMock()
    run = MagicMock()
    run.id = uuid.uuid4()
    with (
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel._resolve_pipeline_run_v1",
            return_value=run,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.evaluate_aa1_phase_chain_v1",
            return_value={"gate_id": "AA1", "verdict": "PASS", "pass": True, "criterion": "", "detail": "", "evidence": {}},
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.evaluate_aa2_traversal_propagation_v1",
            return_value={"gate_id": "AA2", "verdict": "PASS", "pass": True, "criterion": "", "detail": "", "evidence": {}},
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.evaluate_aa3_tcre_jobs_v1",
            return_value={"gate_id": "AA3", "verdict": "PASS", "pass": True, "criterion": "", "detail": "", "evidence": {}},
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.evaluate_aa4_retrieval_spread_v1",
            return_value={"gate_id": "AA4", "verdict": "ADVISORY", "pass": False, "criterion": "", "detail": "", "evidence": {}},
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.evaluate_aa5_synthesis_started_v1",
            return_value={"gate_id": "AA5", "verdict": "PASS", "pass": True, "criterion": "", "detail": "", "evidence": {}},
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.evaluate_aa6_forward_progress_v1",
            return_value={"gate_id": "AA6", "verdict": "PASS", "pass": True, "criterion": "", "detail": "", "evidence": {}},
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.evaluate_aa7_no_wedge_scripts_v1",
            return_value={"gate_id": "AA7", "verdict": "PASS", "pass": True, "criterion": "", "detail": "", "evidence": {}},
        ),
    ):
        panel = build_continuity_proof_panel_v1(session, tenant_id=tenant_id, wedge_free_ack=True)
    assert panel["surface_kind"] == "continuity_proof_panel"
    assert set(panel["gates"].keys()) == set(AA_GATE_IDS_V1)


def test_p2_2_proof_passes_when_panel_complete() -> None:
    panel = {
        "surface_kind": "continuity_proof_panel",
        "gate_order": list(AA_GATE_IDS_V1),
        "gates": {gid: {"gate_id": gid, "verdict": "PASS"} for gid in AA_GATE_IDS_V1},
        "summary": {"pass_count": 7, "fail_count": 0, "advisory_count": 0, "m3_autonomously_alive": True},
    }
    text = format_continuity_proof_panel_text_v1(
        {
            **panel,
            "tenant_id": "t",
            "evaluated_at": "now",
            "window_hours": 24,
        }
    )
    proof = evaluate_p2_2_proof_panel_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        panel=panel,
        panel_text=text,
    )
    assert proof["p2_2_pass"] is True
