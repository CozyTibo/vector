"""Step 8 Fix 3–5 verification."""

from __future__ import annotations

import inspect

from vector.domains.cortex.execution.scheduling import verify_phase03_identity_projection_boundary_v1
from vector.domains.cortex.identity import continuity_rebuild as id_mod
from vector.domains.cortex.unlock.step08_fixes_shipped import (
    evaluate_fix3_promotion_hook_v1,
    evaluate_fix4_backfill_candidate_regen_v1,
    evaluate_fix5_admin_operator_routes_v1,
    evaluate_step08_fixes_shipped_v1,
)


def test_fix3_phase03_promotion_hook() -> None:
    ok, _ = evaluate_fix3_promotion_hook_v1()
    assert ok is True
    assert verify_phase03_identity_projection_boundary_v1() == []
    from vector.domains.cortex.identity import identity_substrate_repair_v1 as repair_mod

    src = inspect.getsource(repair_mod.run_identity_substrate_repair_slice_v1)
    assert "schedule_graph_density_pass_v1" in src


def test_fix4_backfill_include_candidate_regen() -> None:
    ok, _ = evaluate_fix4_backfill_candidate_regen_v1()
    assert ok is True


def test_fix5_admin_routes_registered() -> None:
    ok, _ = evaluate_fix5_admin_operator_routes_v1()
    assert ok is True


def test_step08_aggregate_passes() -> None:
    out = evaluate_step08_fixes_shipped_v1()
    assert out["step8_pass"] is True
    assert out["fix3_pass"] is True
    assert out["fix4_pass"] is True
    assert out["fix5_pass"] is True
