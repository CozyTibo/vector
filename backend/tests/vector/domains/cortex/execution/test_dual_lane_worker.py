"""P2-A — dual-lane worker budgets and schedule."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from vector.domains.cortex.execution.dual_lane_worker import (
    canonical_lane_owed_v1,
    evaluate_dual_lane_schedule_v1,
    execution_lane_owed_v1,
    resolve_dual_lane_budgets_v1,
)
from vector.domains.cortex.execution.tenant_constants import LEASE_STATUS_WAITING
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_07_RETRIEVAL,
)


def test_resolve_dual_lane_budgets_splits_total() -> None:
    cfg = MagicMock()
    cfg.cortex_convergence_time_budget_seconds = 300
    cfg.cortex_execution_canonical_lane_budget_seconds = 0
    cfg.cortex_execution_execution_lane_budget_seconds = 0
    total, canon, exec_b = resolve_dual_lane_budgets_v1(cfg)
    assert total == 300
    assert canon >= 30
    assert exec_b >= 30
    assert canon + exec_b <= total


def test_execution_lane_not_owed_when_waiting_on_tcre() -> None:
    lease = MagicMock()
    lease.block_reason_code = None
    lease.fsm_state = "AWAITING_TCRE"
    lease.status = LEASE_STATUS_WAITING
    lease.phase_cursor = PHASE_07_RETRIEVAL
    lease.detail_json = {"waiting_reason": "tcre_async"}
    assert execution_lane_owed_v1(lease) is False


def test_execution_lane_owed_at_phase_05() -> None:
    lease = MagicMock()
    lease.block_reason_code = None
    lease.fsm_state = "TRAVERSAL"
    lease.status = "running"
    lease.phase_cursor = "phase_05_traversal"
    lease.detail_json = {}
    assert execution_lane_owed_v1(lease) is True


def test_canonical_parallel_schedule() -> None:
    lease = MagicMock()
    lease.block_reason_code = None
    lease.fsm_state = "AWAITING_TCRE"
    lease.status = LEASE_STATUS_WAITING
    lease.phase_cursor = PHASE_07_RETRIEVAL
    lease.detail_json = {"waiting_reason": "tcre_async"}
    session = MagicMock()
    with (
        patch(
            "vector.domains.cortex.execution.dual_lane_worker.is_execution_dual_lane_enabled_v1",
            return_value=True,
        ),
        patch(
            "vector.domains.cortex.execution.dual_lane_worker.canonical_lane_owed_v1",
            return_value=True,
        ),
    ):
        sched = evaluate_dual_lane_schedule_v1(
            session,
            tenant_id=uuid.uuid4(),
            lease=lease,
            bundle_id="bundle-1",
        )
    assert sched["canonical_parallel_while_execution"] is True
    assert sched["canonical_lane_owed"] is True
    assert sched["execution_lane_owed"] is False


def test_run_tenant_convergence_dispatches_dual_lane() -> None:
    import inspect

    from vector.domains.cortex.execution import run_tenant_execution as rte

    src = inspect.getsource(rte.run_tenant_convergence_v1)
    assert "run_dual_lane_convergence_v1" in src
    assert "is_execution_dual_lane_enabled_v1" in src
