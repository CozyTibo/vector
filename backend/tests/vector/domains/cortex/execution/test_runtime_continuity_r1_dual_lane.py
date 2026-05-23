"""R1 — execution lane must run when canonical returns topology_wait."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from vector.domains.cortex.execution.dual_lane_worker import (
    resolve_canonical_lane_budget_for_slice_v1,
    run_dual_lane_convergence_v1,
)
from vector.domains.cortex.execution.tenant_constants import LEASE_STATUS_DIRTY
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL


def test_canonical_budget_capped_when_execution_owed() -> None:
    cfg = MagicMock()
    cfg.cortex_dual_lane_canonical_cap_when_execution_owed_seconds = 90
    assert resolve_canonical_lane_budget_for_slice_v1(cfg, base_canonical_budget=180, execution_lane_owed=True) == 90
    assert resolve_canonical_lane_budget_for_slice_v1(cfg, base_canonical_budget=180, execution_lane_owed=False) == 180


def test_topology_wait_does_not_skip_execution_lane() -> None:
    tenant_id = uuid.uuid4()
    pipeline_run_id = uuid.uuid4()
    lease = MagicMock()
    lease.tenant_id = tenant_id
    lease.pipeline_run_id = pipeline_run_id
    lease.phase_cursor = PHASE_07_RETRIEVAL
    lease.status = LEASE_STATUS_DIRTY
    lease.fsm_state = "RETRIEVAL"
    lease.block_reason_code = None
    lease.detail_json = {}
    lease.obligation_epoch = 10
    lease.target_epoch = 9

    session = MagicMock()
    cfg = MagicMock()
    cfg.cortex_convergence_time_budget_seconds = 300
    cfg.cortex_execution_canonical_lane_budget_seconds = 0
    cfg.cortex_execution_execution_lane_budget_seconds = 0
    cfg.cortex_post_ingestion_canonical_batch_limit = 50
    cfg.cortex_canonical_topology_wait_cooldown_seconds = 60
    cfg.cortex_canonical_deferral_retry_storm_cooldown_seconds = 300
    cfg.cortex_dual_lane_run_execution_on_topology_wait = True
    cfg.cortex_dual_lane_canonical_cap_when_execution_owed_seconds = 90
    cfg.cortex_execution_heartbeat_reset_cursor_to_phase05 = False

    canon_result = {
        "lane": "canonical",
        "outcome": "canonical_topology_wait",
        "canonical_outcome": "topology_wait",
    }
    exec_result = {"lane": "execution", "outcome": "execution_lane_idle"}

    with (
        patch(
            "vector.domains.cortex.synthesis.synthesis_job_lifecycle.maybe_reconcile_synthesis_jobs_on_materialize_v1",
        ),
        patch(
            "vector.domains.cortex.execution.dual_lane_worker.evaluate_dual_lane_schedule_v1",
            return_value={
                "canonical_lane_owed": True,
                "execution_lane_owed": True,
                "execution_phase_cursor": PHASE_07_RETRIEVAL,
            },
        ),
        patch(
            "vector.domains.cortex.execution.dual_lane_worker._run_canonical_lane_slice_v1",
            return_value=canon_result,
        ) as canon_mock,
        patch(
            "vector.domains.cortex.execution.dual_lane_worker._run_execution_lane_slice_v1",
            return_value=exec_result,
        ) as exec_mock,
        patch(
            "vector.domains.cortex.operational_runtime.graph_density_promotion.schedule_graph_density_promotion_on_convergence_worker_v1",
            return_value={},
        ),
        patch("vector.domains.cortex.execution.dual_lane_worker.emit_execution_path_telemetry_v1"),
        patch("vector.domains.cortex.execution.dual_lane_worker.sync_dual_lane_fields_on_lease_v1"),
        patch("vector.domains.cortex.execution.dual_lane_worker.enqueue_tenant_convergence_v1"),
    ):
        out = run_dual_lane_convergence_v1(
            session,
            tenant_id=tenant_id,
            lease=lease,
            pipeline_run_id=pipeline_run_id,
            bundle_id="bundle-1",
            cfg=cfg,
            started=0.0,
            reason="test",
        )

    exec_mock.assert_called_once()
    canon_mock.assert_called_once()
    assert out["dual_lane"]["execution_lane_ran"] is True
    assert out["dual_lane"].get("canonical_topology_nonblocking") is True
