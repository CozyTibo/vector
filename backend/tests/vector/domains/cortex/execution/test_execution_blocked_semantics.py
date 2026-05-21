"""TRUE P0B — execution stop semantics tied to phase receipts."""

from __future__ import annotations

from vector.domains.cortex.execution.phase_outcomes import (
    WORKER_OUTCOME_CANONICAL_TOPOLOGY_WAIT,
    is_topology_blocked_phase02_v1,
    is_waiting_async_phase06_v1,
)
from vector.domains.cortex.execution.scheduling import verify_execution_blocked_semantics_v1
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_BLOCKED,
    PHASE_OUTCOME_WAITING_ASYNC,
)


def test_verify_execution_blocked_semantics() -> None:
    assert verify_execution_blocked_semantics_v1() == []


def test_topology_blocked_from_receipt() -> None:
    out = {
        "outcome": PHASE_OUTCOME_BLOCKED,
        "blocked_reason": "topology_wait",
        "substrate_phase_receipt": {
            "outcome": PHASE_OUTCOME_BLOCKED,
            "blocked_reason": "topology_wait",
        },
    }
    assert is_topology_blocked_phase02_v1(out) is True


def test_waiting_async_phase06() -> None:
    out = {"outcome": PHASE_OUTCOME_WAITING_ASYNC, "async": True, "job_id": "j1"}
    assert is_waiting_async_phase06_v1(out) is True


def test_worker_topology_wait_label() -> None:
    from vector.domains.cortex.execution.phase_outcomes import (
        worker_outcome_label_for_phase02_continue_v1,
    )

    out = {"outcome": PHASE_OUTCOME_BLOCKED, "blocked_reason": "topology_wait"}
    label = worker_outcome_label_for_phase02_continue_v1(
        phase_output=out,
        canonical_summary={"canonical_outcome": "topology_wait", "progress_made": False},
    )
    assert label == WORKER_OUTCOME_CANONICAL_TOPOLOGY_WAIT
