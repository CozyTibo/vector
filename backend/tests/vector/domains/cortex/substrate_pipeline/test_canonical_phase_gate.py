"""M1 — canonical→identity gate shared by convergence and legacy Celery."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from vector.domains.cortex.canonical.forward_progress.constants import (
    CANONICAL_OUTCOME_PARTIAL_PROGRESS,
    CANONICAL_OUTCOME_TOPOLOGY_WAIT,
)
from vector.domains.cortex.substrate_pipeline.canonical_phase_gate import (
    canonical_may_advance_to_identity_v1,
    canonical_needs_more_work_v1,
    evaluate_legacy_canonical_chain_gate_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_STATUS_FAILED,
    PHASE_STATUS_WAITING,
)


def test_canonical_needs_more_work_topology_wait() -> None:
    session = MagicMock()
    summary = {"canonical_outcome": CANONICAL_OUTCOME_TOPOLOGY_WAIT}
    assert canonical_needs_more_work_v1(session, canonical_summary=summary, tenant_id=uuid.uuid4()) is True


def test_canonical_needs_more_work_skipped_bundle() -> None:
    session = MagicMock()
    assert (
        canonical_needs_more_work_v1(
            session,
            canonical_summary={"skipped": True},
            tenant_id=uuid.uuid4(),
        )
        is False
    )


def test_canonical_may_advance_blocks_waiting_zero_progress() -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    prid = uuid.uuid4()
    phase_run = MagicMock(status=PHASE_STATUS_WAITING)
    with patch(
        "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.get_phase_run_v1",
        return_value=phase_run,
    ):
        may, reason = canonical_may_advance_to_identity_v1(
            session,
            tenant_id=tid,
            pipeline_run_id=prid,
            phase_output={
                "canonical_summary": {
                    "canonical_outcome": CANONICAL_OUTCOME_TOPOLOGY_WAIT,
                    "total_succeeded": 0,
                },
            },
        )
    assert may is False
    assert reason == "canonical_topology_wait_zero_progress"


def test_canonical_may_advance_blocks_failed_zero_progress() -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    prid = uuid.uuid4()
    phase_run = MagicMock(status=PHASE_STATUS_FAILED)
    with patch(
        "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.get_phase_run_v1",
        return_value=phase_run,
    ):
        may, reason = canonical_may_advance_to_identity_v1(
            session,
            tenant_id=tid,
            pipeline_run_id=prid,
            phase_output={
                "canonical_summary": {"canonical_outcome": "failed", "total_succeeded": 0},
            },
        )
    assert may is False
    assert reason == "canonical_materialization_failed_zero_progress"


def test_evaluate_legacy_gate_disabled_always_chains() -> None:
    session = MagicMock()
    out = evaluate_legacy_canonical_chain_gate_v1(
        session,
        tenant_id=uuid.uuid4(),
        pipeline_run_id=uuid.uuid4(),
        phase_output={},
        gate_enabled=False,
    )
    assert out["may_chain"] is True
    assert out["gate_enabled"] is False


def test_legacy_phase_task_blocks_chain_after_canonical_waiting() -> None:
    from app.tasks.cortex_substrate_pipeline import run_cortex_substrate_pipeline_phase_task

    tid = uuid.uuid4()
    prid = uuid.uuid4()
    phase_out = {
        "canonical_summary": {
            "canonical_outcome": CANONICAL_OUTCOME_TOPOLOGY_WAIT,
            "total_succeeded": 0,
        },
    }
    with (
        patch("app.tasks.cortex_substrate_pipeline.session_scope") as scope,
        patch(
            "app.tasks.cortex_substrate_pipeline.run_phase_02_canonical_v1",
            return_value=phase_out,
        ),
        patch(
            "app.tasks.cortex_substrate_pipeline.evaluate_legacy_canonical_chain_gate_v1",
            return_value={
                "may_chain": False,
                "reason": "canonical_topology_wait_zero_progress",
                "gate_enabled": True,
            },
        ),
        patch("app.tasks.cortex_substrate_pipeline.get_settings") as gs,
    ):
        gs.return_value.cortex_substrate_pipeline_canonical_chain_gate_enabled = True
        mock_session = scope.return_value.__enter__.return_value
        result = run_cortex_substrate_pipeline_phase_task(
            str(tid),
            str(prid),
            "phase_02_canonical",
        )
    assert result["chained"] is False
    assert result.get("deprecated") is True
    assert result.get("hint") == "blocked"
    gate = result.get("canonical_chain_gate") or {}
    assert gate.get("may_chain") is False
    assert gate.get("reason") == "canonical_topology_wait_zero_progress"
    mock_session.commit.assert_called()


def test_legacy_phase_task_chains_when_gate_allows() -> None:
    from app.tasks.cortex_substrate_pipeline import run_cortex_substrate_pipeline_phase_task

    tid = uuid.uuid4()
    prid = uuid.uuid4()
    with (
        patch("app.tasks.cortex_substrate_pipeline.session_scope") as scope,
        patch(
            "app.tasks.cortex_substrate_pipeline.run_phase_02_canonical_v1",
            return_value={"canonical_summary": {"canonical_outcome": "progressed", "total_succeeded": 5}},
        ),
        patch(
            "app.tasks.cortex_substrate_pipeline.evaluate_legacy_canonical_chain_gate_v1",
            return_value={"may_chain": True, "reason": None, "gate_enabled": True},
        ),
        patch("app.tasks.cortex_substrate_pipeline.get_settings") as gs,
    ):
        gs.return_value.cortex_substrate_pipeline_canonical_chain_gate_enabled = True
        scope.return_value.__enter__.return_value
        result = run_cortex_substrate_pipeline_phase_task(
            str(tid),
            str(prid),
            "phase_02_canonical",
        )
    assert result["chained"] is False
    assert result.get("deprecated") is True
    assert result.get("hint") == "enqueue_execution_slice"


def test_canonical_needs_more_work_partial_progress() -> None:
    session = MagicMock()
    summary = {"canonical_outcome": CANONICAL_OUTCOME_PARTIAL_PROGRESS}
    assert canonical_needs_more_work_v1(session, canonical_summary=summary, tenant_id=uuid.uuid4()) is True
