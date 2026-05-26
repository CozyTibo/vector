"""Wave 7 — HTTP 410 for collapsed primary-nav admin routes."""

from __future__ import annotations

from typing import NoReturn

from vector.domains.cortex.execution.admin_deprecation import raise_admin_endpoint_gone


def raise_identity_replay_jobs_primary_route_gone_v1() -> NoReturn:
    """Legacy ``/cortex/identity/replay-jobs`` — use debug routes only."""
    raise_admin_endpoint_gone(
        deprecated="/admin/tenants/{tenant_id}/cortex/identity/replay-jobs",
        replacement="/admin/tenants/{tenant_id}/cortex/debug/identity/replay-jobs",
        migration="Wave 7: replay jobs are debug-only; operator repair uses POST .../cortex/operator/actions.",
    )

