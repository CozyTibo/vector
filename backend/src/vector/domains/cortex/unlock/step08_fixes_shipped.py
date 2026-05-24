"""War-room step 8 — Fix 3–5 shipped verification (promotion hook + admin APIs)."""

from __future__ import annotations

import importlib
import inspect
from typing import Any


def evaluate_fix3_promotion_hook_v1() -> tuple[bool, str]:
    """Fix 3: phase-03 identity substrate schedules lawful promotion inline."""
    from vector.domains.cortex.execution.scheduling import verify_phase03_identity_projection_boundary_v1
    from vector.domains.cortex.identity import continuity_rebuild as id_mod

    errors = verify_phase03_identity_projection_boundary_v1()
    if errors:
        return False, f"phase03_boundary:{','.join(errors)}"
    if not callable(getattr(id_mod, "schedule_graph_density_promotion_after_identity_substrate_v1", None)):
        return False, "missing_schedule_graph_density_promotion_after_identity_substrate_v1"
    return True, "phase03_graph_density_promotion_hook"


def evaluate_fix4_backfill_candidate_regen_v1() -> tuple[bool, str]:
    """Fix 4: admin backfill request exposes include_candidate_regen."""
    from vector.contracts.admin import AdminCortexIdentityBackfillFromAnchorsRequest

    fields = AdminCortexIdentityBackfillFromAnchorsRequest.model_fields
    if "include_candidate_regen" not in fields:
        return False, "missing_include_candidate_regen_field"
    if fields["include_candidate_regen"].default is not True:
        return False, "include_candidate_regen_default_not_true"
    admin_mod = importlib.import_module("vector.api.http.routes.admin")
    src = inspect.getsource(admin_mod.build_admin_router)
    if "run_identity_handles_and_candidates_refresh" not in src:
        return False, "backfill_route_missing_candidates_refresh"
    return True, "backfill_include_candidate_regen"


def evaluate_fix5_admin_operator_routes_v1() -> tuple[bool, str]:
    """Fix 5: tenant POST routes for promotion pass and org-link replay enqueue/run."""
    from vector.domains.cortex.execution.admin_bypass_guard import verify_no_admin_bypass_routes_registered_v1

    bypass_errors = verify_no_admin_bypass_routes_registered_v1()
    if bypass_errors:
        return False, f"admin_bypass:{','.join(bypass_errors)}"

    admin_mod = importlib.import_module("vector.api.http.routes.admin")
    admin_src = inspect.getsource(admin_mod.build_admin_router)
    if "identity/replay-jobs/run" not in admin_src:
        return False, "missing_identity_replay_jobs_run_route"
    if "identity/replay-jobs/enqueue" not in admin_src:
        return False, "missing_identity_replay_jobs_enqueue_route"
    return True, "admin_promotion_and_replay_routes"


def evaluate_step08_fixes_shipped_v1() -> dict[str, Any]:
    """Aggregate Fix 3–5 checks for war-room step 8 artifact."""
    fix3_ok, fix3_detail = evaluate_fix3_promotion_hook_v1()
    fix4_ok, fix4_detail = evaluate_fix4_backfill_candidate_regen_v1()
    fix5_ok, fix5_detail = evaluate_fix5_admin_operator_routes_v1()
    all_ok = fix3_ok and fix4_ok and fix5_ok
    return {
        "step": 8,
        "fix3_pass": fix3_ok,
        "fix3_detail": fix3_detail,
        "fix4_pass": fix4_ok,
        "fix4_detail": fix4_detail,
        "fix5_pass": fix5_ok,
        "fix5_detail": fix5_detail,
        "step8_pass": all_ok,
    }
