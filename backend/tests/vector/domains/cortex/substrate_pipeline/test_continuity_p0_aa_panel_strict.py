"""Phase A step A4 — strict AA1/AA6 proof panel gates."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from vector.domains.cortex.substrate_pipeline.continuity_p0_aa_panel_strict import (
    evaluate_p0_a4_aa_panel_strict_proof_v1,
    verify_a4_aa_panel_strict_wiring_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
    AA_GATE_IDS_V1,
    _lawful_empty_synthesis_v1,
    evaluate_aa1_phase_chain_v1,
    evaluate_aa6_forward_progress_v1,
    format_continuity_proof_panel_text_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    PHASE_STATUS_COMPLETED,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_COMPLETED_EMPTY,
)


def test_a4_wiring_static() -> None:
    wiring = verify_a4_aa_panel_strict_wiring_v1()
    assert wiring["wiring_ok"] is True


def test_lawful_empty_requires_documentation() -> None:
    assert _lawful_empty_synthesis_v1(
        {
            "scope_empty": True,
            "jobs_completed": 0,
            "phase_08_outcome": PHASE_OUTCOME_COMPLETED_EMPTY,
        }
    )
    assert not _lawful_empty_synthesis_v1(
        {"scope_empty": False, "jobs_completed": 0, "phase_08_outcome": "COMPLETED"}
    )
    assert not _lawful_empty_synthesis_v1(
        {"scope_empty": True, "jobs_completed": 0, "empty_scope_reason": ""}
    )


def test_aa1_fails_on_scope_empty_with_retrieval_entries() -> None:
    tenant_id = uuid.uuid4()
    run_id = uuid.uuid4()
    run = MagicMock()
    run.id = run_id
    lease = MagicMock()
    lease.status = "active"
    lease.attempt_count = 0
    lease.last_error = None

    def _phase_row(status: str, *, output: dict | None = None) -> MagicMock:
        row = MagicMock()
        row.status = status
        row.started_at = None
        row.completed_at = None
        row.output_json = output or {}
        return row

    def _get_phase(_session, *, pipeline_run_id, phase_id):  # noqa: ANN001
        if phase_id == PHASE_08_SYNTHESIS:
            return _phase_row(
                PHASE_STATUS_COMPLETED,
                output={
                    "outcome": PHASE_OUTCOME_COMPLETED_EMPTY,
                    "jobs_completed": 0,
                    "scope_empty": True,
                    "retrieval_entries_in_epoch": 100,
                },
            )
        return _phase_row(PHASE_STATUS_COMPLETED)

    session = MagicMock()
    with (
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel._resolve_pipeline_run_v1",
            return_value=run,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.get_tenant_execution_lease_v1",
            return_value=lease,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.get_phase_run_v1",
            side_effect=_get_phase,
        ),
    ):
        gate = evaluate_aa1_phase_chain_v1(session, tenant_id=tenant_id, pipeline_run_id=run_id)
    assert gate["verdict"] == "FAIL"
    assert gate["evidence"]["lawful_empty"] is False


def test_aa1_fails_on_completed_empty_without_lawful_proof() -> None:
    tenant_id = uuid.uuid4()
    run_id = uuid.uuid4()
    run = MagicMock()
    run.id = run_id
    lease = MagicMock()
    lease.status = "active"
    lease.attempt_count = 0
    lease.last_error = None

    def _phase_row(status: str, *, output: dict | None = None) -> MagicMock:
        row = MagicMock()
        row.status = status
        row.started_at = None
        row.completed_at = None
        row.output_json = output or {}
        return row

    def _get_phase(_session, *, pipeline_run_id, phase_id):  # noqa: ANN001
        if phase_id == PHASE_08_SYNTHESIS:
            return _phase_row(
                PHASE_STATUS_COMPLETED,
                output={
                    "outcome": PHASE_OUTCOME_COMPLETED_EMPTY,
                    "jobs_completed": 0,
                    "scope_empty": False,
                },
            )
        return _phase_row(PHASE_STATUS_COMPLETED)

    session = MagicMock()
    with (
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel._resolve_pipeline_run_v1",
            return_value=run,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.get_tenant_execution_lease_v1",
            return_value=lease,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.get_phase_run_v1",
            side_effect=_get_phase,
        ),
    ):
        gate = evaluate_aa1_phase_chain_v1(session, tenant_id=tenant_id, pipeline_run_id=run_id)
    assert gate["verdict"] == "FAIL"
    assert gate["evidence"]["jobs_completed"] == 0
    assert gate["evidence"]["lawful_empty"] is False


def test_aa6_fails_without_forward_progress_signals() -> None:
    tenant_id = uuid.uuid4()
    session = MagicMock()
    session.scalars.return_value.all.return_value = []
    with (
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.resolve_default_bundle_id_for_stub_transform",
            return_value=uuid.uuid4(),
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.list_untreated_routable_count_estimate",
            return_value=42,
        ),
    ):
        gate = evaluate_aa6_forward_progress_v1(session, tenant_id=tenant_id, window_hours=24)
    assert gate["verdict"] == "FAIL"
    assert gate["evidence"]["mat_only_pass"] is True
    assert gate["evidence"]["forward_progress_signals"] == []


def test_aa6_passes_when_untreated_decreases_in_window() -> None:
    tenant_id = uuid.uuid4()
    row_first = MagicMock()
    row_first.output_json = {
        "canonical_summary": {
            "total_succeeded": 0,
            "progress_made": False,
            "untreated_routable_estimate": 50,
        }
    }
    row_last = MagicMock()
    row_last.output_json = {
        "canonical_summary": {
            "total_succeeded": 0,
            "progress_made": False,
            "untreated_routable_estimate": 40,
        }
    }
    session = MagicMock()
    session.scalars.return_value.all.return_value = [row_first, row_last]
    with (
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.resolve_default_bundle_id_for_stub_transform",
            return_value=uuid.uuid4(),
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.continuity_proof_panel.list_untreated_routable_count_estimate",
            return_value=40,
        ),
    ):
        gate = evaluate_aa6_forward_progress_v1(session, tenant_id=tenant_id, window_hours=24)
    assert gate["verdict"] == "PASS"
    assert "untreated_routable_decreased" in gate["evidence"]["forward_progress_signals"]


def test_a4_proof_passes_when_strict_panel_wired() -> None:
    panel = {
        "strict_aa_panel_schema_version": 2,
        "gate_order": list(AA_GATE_IDS_V1),
        "gates": {
            "AA1": {
                "gate_id": "AA1",
                "verdict": "FAIL",
                "evidence": {
                    "phase_08": {"jobs_completed": 0, "phase_08_status": "completed"},
                    "jobs_completed": 0,
                    "lawful_empty": False,
                },
            },
            "AA6": {
                "gate_id": "AA6",
                "verdict": "FAIL",
                "evidence": {
                    "mat_only_pass": True,
                    "forward_progress_signals": [],
                    "convergence_delta_succeeded": 0,
                },
            },
        },
        "summary": {"m3_autonomously_alive": False},
    }
    text = format_continuity_proof_panel_text_v1(
        {
            **panel,
            "tenant_id": "t",
            "evaluated_at": "now",
            "window_hours": 24,
        }
    )
    proof = evaluate_p0_a4_aa_panel_strict_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        panel=panel,
        panel_text=text,
    )
    assert proof["p0_a4_pass"] is True
