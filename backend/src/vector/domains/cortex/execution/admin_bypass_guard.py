"""Wave 4 — ensure admin HTTP surface has no substrate bypass mutation routes."""

from __future__ import annotations

import importlib
import inspect
from typing import Final

# Path fragments that must not appear in admin route registration modules.
FORBIDDEN_ADMIN_ROUTE_FRAGMENTS_V1: Final[tuple[str, ...]] = (
    "materialize-backlog",
    "flush-rerun",
    "progression/continue",
    'cortex/canonical/transform/materialize"',
    "canonical/replay-jobs/run",
    "canonical/replay-jobs/{job_id}/resume",
    "identity/replay-jobs/run",
    "identity/replay-jobs/enqueue",
    "identity/rebuild-continuity",
    "identity/link-candidates/regenerate-async",
    "identity/authoritative-replay-async",
    "reasoning/runtime/reconstruct",
    "/retrieval/index/rebuild",
    "/retrieval/index/bootstrap",
    "synthesis/jobs/run",
    "synthesis/jobs/resynthesize",
    "substrate-pipeline/stalled/{pipeline_run_id}/recover",
    "continuity-watchdog/run",
    "operational-runtime/graph-density-promotion/run",
    "operational-runtime/graph-density-promotion/schedule",
    "operational-runtime/traversal-scheduling/schedule",
    "operational-runtime/traversal-scheduling/run",
    "operational-runtime/traversal-retry/run",
    "operational-runtime/traversal-retry/schedule",
    "operational-runtime/stalled-traversal-recovery/run",
    "operational-runtime/stalled-traversal-recovery/schedule",
    "operational-runtime/tcre-saturation-scheduling/run",
    "operational-runtime/tcre-saturation-scheduling/schedule",
    "operational-runtime/synthesis-activation-scheduling/run",
    "operational-runtime/synthesis-activation-scheduling/schedule",
    "operational-runtime/graph-orphan-continuity/stitch",
)

_ADMIN_ROUTE_MODULES_V1: Final[tuple[str, ...]] = (
    "vector.api.http.routes.admin",
    "vector.api.http.routes.admin_substrate_pipeline",
    "vector.api.http.routes.admin_cortex_retrieval",
    "vector.api.http.routes.admin_cortex_synthesis",
    "vector.api.http.routes.admin_cortex_operational_runtime",
)


def verify_no_admin_bypass_routes_registered_v1() -> list[str]:
    """Return error codes if forbidden bypass paths or 410 stubs remain registered."""
    errors: list[str] = []
    for mod_name in _ADMIN_ROUTE_MODULES_V1:
        mod = importlib.import_module(mod_name)
        try:
            src = inspect.getsource(mod)
        except OSError:
            errors.append(f"uninspectable_module:{mod_name}")
            continue
        for frag in FORBIDDEN_ADMIN_ROUTE_FRAGMENTS_V1:
            if frag in src:
                errors.append(f"bypass_route_registered:{mod_name}:{frag}")
        if "raise_admin_endpoint_gone" in src:
            errors.append(f"admin_410_stub_remaining:{mod_name}")
    return errors
