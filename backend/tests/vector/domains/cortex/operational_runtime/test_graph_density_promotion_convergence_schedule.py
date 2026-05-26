"""D3 — convergence worker schedules inline graph-density promotion."""

from __future__ import annotations

from vector.domains.cortex.execution.scheduling import verify_d3_graph_promotion_on_convergence_worker_v1
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    PROMOTION_TRIGGER_CONVERGENCE_SLICE_V1,
    build_graph_density_promotion_catalog_v1,
)


def test_d3_catalog_exposes_convergence_slice_trigger() -> None:
    cat = build_graph_density_promotion_catalog_v1()
    assert PROMOTION_TRIGGER_CONVERGENCE_SLICE_V1 in cat["promotion_triggers"]
    assert cat["convergence_worker_schedule_enabled"] is False
    assert cat["authoritative_promotion_path"] == "run_identity_substrate_repair_slice_v1"


def test_d3_static_wiring() -> None:
    assert verify_d3_graph_promotion_on_convergence_worker_v1() == []
