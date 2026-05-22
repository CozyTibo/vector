"""P1-F — dual-lane lease semantics."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from vector.domains.cortex.execution.dual_lane_lease import (
    DETAIL_KEY_CANONICAL_LANE_V1,
    DETAIL_KEY_EXECUTION_LANE_V1,
    build_canonical_lane_detail_v1,
    build_execution_lane_detail_v1,
    is_execution_lane_phase_cursor_v1,
    should_mark_execution_lane_stalled_v1,
    sync_dual_lane_fields_on_lease_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_05_TRAVERSAL,
    PHASE_07_RETRIEVAL,
)


def test_execution_lane_phase_cursor_set() -> None:
    assert is_execution_lane_phase_cursor_v1(PHASE_05_TRAVERSAL) is True
    assert is_execution_lane_phase_cursor_v1(PHASE_02_CANONICAL) is False


def test_should_not_stall_on_canonical_cursor() -> None:
    lease = MagicMock()
    lease.phase_cursor = PHASE_02_CANONICAL
    with patch(
        "vector.domains.cortex.execution.dual_lane_lease.is_execution_dual_lane_enabled_v1",
        return_value=True,
    ):
        assert should_mark_execution_lane_stalled_v1(lease) is False
    lease.phase_cursor = PHASE_07_RETRIEVAL
    with patch(
        "vector.domains.cortex.execution.dual_lane_lease.is_execution_dual_lane_enabled_v1",
        return_value=True,
    ):
        assert should_mark_execution_lane_stalled_v1(lease) is True


def test_sync_dual_lane_persists_detail_keys() -> None:
    lease = MagicMock()
    lease.tenant_id = uuid.uuid4()
    lease.detail_json = {}
    lease.fsm_state = "AWAITING_TCRE"
    lease.status = "waiting"
    lease.phase_cursor = PHASE_07_RETRIEVAL
    lease.block_reason_code = None
    lease.last_error = None
    lease.pipeline_run_id = uuid.uuid4()
    session = MagicMock()
    with (
        patch(
            "vector.domains.cortex.execution.dual_lane_lease.is_execution_dual_lane_enabled_v1",
            return_value=True,
        ),
        patch(
            "vector.domains.cortex.execution.dual_lane_lease.resolve_default_bundle_id_for_stub_transform",
            return_value=None,
        ),
    ):
        out = sync_dual_lane_fields_on_lease_v1(session, lease=lease)
    assert DETAIL_KEY_CANONICAL_LANE_V1 in lease.detail_json
    assert DETAIL_KEY_EXECUTION_LANE_V1 in lease.detail_json
    assert out["canonical_lane"]["lane"] == "canonical"
    assert out["execution_lane"]["lane"] == "execution"


def test_build_execution_lane_waiting_status() -> None:
    lease = MagicMock()
    lease.detail_json = {"waiting_reason": "tcre_async"}
    lease.fsm_state = "AWAITING_TCRE"
    lease.status = "waiting"
    lease.phase_cursor = PHASE_07_RETRIEVAL
    lease.block_reason_code = None
    lease.last_error = None
    lease.pipeline_run_id = uuid.uuid4()
    out = build_execution_lane_detail_v1(MagicMock(), tenant_id=uuid.uuid4(), lease=lease)
    assert out["lane_status"] == "WAITING"
    assert out["waiting_reason"] == "tcre_async"


def test_build_canonical_lane_topology_wait() -> None:
    lease = MagicMock()
    from vector.domains.cortex.canonical.forward_progress.constants import (
        CANONICAL_OUTCOME_TOPOLOGY_WAIT,
    )

    lease.detail_json = {"last_canonical_outcome": CANONICAL_OUTCOME_TOPOLOGY_WAIT}
    lease.fsm_state = "CANONICAL_DRAINING"
    lease.status = "dirty"
    session = MagicMock()
    with (
        patch(
            "vector.domains.cortex.execution.dual_lane_lease.resolve_default_bundle_id_for_stub_transform",
            return_value="bundle-1",
        ),
        patch(
            "vector.domains.cortex.execution.dual_lane_lease.list_untreated_routable_count_estimate",
            return_value=10,
        ),
        patch(
            "vector.domains.cortex.execution.dual_lane_lease.count_deferrals",
            return_value={"deferred_waiting_cooldown": 1},
        ),
        patch(
            "vector.domains.cortex.execution.dual_lane_lease.build_forward_progress_metrics",
            return_value={},
        ),
    ):
        out = build_canonical_lane_detail_v1(session, tenant_id=uuid.uuid4(), lease=lease)
    assert out["lane_status"] == "WAITING"
    assert out["topology_wait"] is True
