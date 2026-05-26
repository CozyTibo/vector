"""Wave 2 — collapsed operator paths."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from vector.domains.cortex.execution.scheduling import verify_wave2_operator_paths_v1
from vector.domains.cortex.identity.identity_substrate_operator_v1 import (
    Wave2CollapsedReplayJobKindError,
    assert_primary_replay_job_kind_allowed_v1,
    operator_rebuild_identities_v1,
)


def test_wave2_static_operator_wiring() -> None:
    assert verify_wave2_operator_paths_v1() == []


def test_collapsed_replay_kinds_blocked_on_primary_api() -> None:
    for kind in ("identity_rebuild_from_anchors", "identity_continuity_rebuild"):
        try:
            assert_primary_replay_job_kind_allowed_v1(kind)
            raise AssertionError(f"expected block for {kind}")
        except Wave2CollapsedReplayJobKindError:
            pass


@patch(
    "vector.domains.cortex.identity.identity_substrate_operator_v1.reset_identity_substrate_repair_state_v1",
    return_value={"anchor_offset": 0},
)
@patch(
    "vector.domains.cortex.identity.identity_substrate_operator_v1.substrate_counts",
    return_value={"identity_anchors": 100},
)
@patch(
    "vector.domains.cortex.execution.convergence_dispatch.mark_dirty_and_enqueue_convergence_v1",
    return_value={"scheduled": True},
)
def test_operator_rebuild_identities_reset_and_dirty(
    _mock_dispatch: MagicMock,
    _mock_counts: MagicMock,
    _mock_reset: MagicMock,
) -> None:
    session = MagicMock()
    out = operator_rebuild_identities_v1(session, tenant_id=uuid.uuid4())
    assert out["no_replay_job"] is True
    assert out["enqueued"] is False
    _mock_reset.assert_called_once()
    _mock_dispatch.assert_called_once()
