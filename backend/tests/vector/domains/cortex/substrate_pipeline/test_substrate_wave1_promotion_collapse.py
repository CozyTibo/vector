"""Wave 1 — single promotion path and honest phase_run.status."""

from __future__ import annotations

import inspect
import uuid
from unittest.mock import MagicMock, patch

from vector.domains.cortex.execution.scheduling import (
    verify_d3_graph_promotion_on_convergence_worker_v1,
    verify_phase03_identity_projection_boundary_v1,
)
from vector.domains.cortex.identity.identity_substrate_phase_helpers_v1 import (
    should_skip_phase_04_after_identity_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
)
from vector.domains.cortex.substrate_pipeline.phase_runner_receipt import (
    _persist_phase_run_for_receipt_outcome_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_BLOCKED,
    PHASE_OUTCOME_COMPLETED,
    PHASE_OUTCOME_COMPLETED_EMPTY,
    PHASE_OUTCOME_FAILED,
)


def test_wave1_static_promotion_wiring() -> None:
    assert verify_d3_graph_promotion_on_convergence_worker_v1() == []
    assert verify_phase03_identity_projection_boundary_v1() == []


def test_persist_blocked_phase02_uses_wait() -> None:
    session = MagicMock()
    out = {
        "substrate_phase_receipt": {
            "outcome": PHASE_OUTCOME_BLOCKED,
            "blocked_reason": "topology_wait",
        }
    }
    with patch(
        "vector.domains.cortex.substrate_pipeline.phase_runner_receipt.wait_phase_v1"
    ) as wait_mock:
        _persist_phase_run_for_receipt_outcome_v1(
            session,
            pipeline_run_id=uuid.uuid4(),
            phase_id=PHASE_02_CANONICAL,
            out=out,
            outcome=PHASE_OUTCOME_BLOCKED,
            blocked_reason="topology_wait",
        )
    wait_mock.assert_called_once()


def test_persist_failed_phase03_uses_fail() -> None:
    session = MagicMock()
    out = {
        "substrate_phase_receipt": {
            "outcome": PHASE_OUTCOME_FAILED,
            "blocked_reason": "identity_substrate_degraded_no_progress",
        }
    }
    with patch(
        "vector.domains.cortex.substrate_pipeline.phase_runner_receipt.fail_phase_v1"
    ) as fail_mock:
        _persist_phase_run_for_receipt_outcome_v1(
            session,
            pipeline_run_id=uuid.uuid4(),
            phase_id=PHASE_03_IDENTITY,
            out=out,
            outcome=PHASE_OUTCOME_FAILED,
        )
    fail_mock.assert_called_once()


def test_persist_phase03_repair_in_progress_uses_wait() -> None:
    session = MagicMock()
    out = {
        "substrate_phase_receipt": {
            "outcome": PHASE_OUTCOME_COMPLETED,
            "blocked_reason": "identity_substrate_repair_in_progress",
        }
    }
    with patch(
        "vector.domains.cortex.substrate_pipeline.phase_runner_receipt.wait_phase_v1"
    ) as wait_mock:
        _persist_phase_run_for_receipt_outcome_v1(
            session,
            pipeline_run_id=uuid.uuid4(),
            phase_id=PHASE_03_IDENTITY,
            out=out,
            outcome=PHASE_OUTCOME_COMPLETED,
            blocked_reason="identity_substrate_repair_in_progress",
        )
    wait_mock.assert_called_once()


def test_persist_phase03_completed_empty_uses_wait() -> None:
    session = MagicMock()
    out = {"substrate_phase_receipt": {"outcome": PHASE_OUTCOME_COMPLETED_EMPTY}}
    with patch(
        "vector.domains.cortex.substrate_pipeline.phase_runner_receipt.wait_phase_v1"
    ) as wait_mock:
        _persist_phase_run_for_receipt_outcome_v1(
            session,
            pipeline_run_id=uuid.uuid4(),
            phase_id=PHASE_03_IDENTITY,
            out=out,
            outcome=PHASE_OUTCOME_COMPLETED_EMPTY,
        )
    wait_mock.assert_called_once()


def test_should_not_skip_phase04_when_degraded() -> None:
    p03 = {
        "substrate_phase_receipt": {"outcome": "COMPLETED_EMPTY"},
        "identity_substrate_health_after": {"status": "degraded"},
        "identity_substrate_audit": {"anchor_backfill": {"entities_upserted": 0}},
        "distinct_candidate_pairs_delta": 0,
    }
    assert should_skip_phase_04_after_identity_v1(p03) is False


def test_run_tenant_convergence_has_no_pre_slice_promotion() -> None:
    from vector.domains.cortex.execution import run_tenant_execution as rte_mod

    src = inspect.getsource(rte_mod.run_tenant_convergence_v1)
    assert "schedule_graph_density_promotion_on_convergence_worker_v1" not in src
