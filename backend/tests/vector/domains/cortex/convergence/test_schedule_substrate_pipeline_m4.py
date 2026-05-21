"""M4: schedule_substrate_pipeline_v1 must not enqueue legacy coordinator."""

from __future__ import annotations

from vector.domains.cortex.convergence.scheduling import (
    verify_schedule_substrate_pipeline_uses_convergence_v1,
)


def test_schedule_substrate_pipeline_static_gate_m4() -> None:
    assert verify_schedule_substrate_pipeline_uses_convergence_v1() == []
