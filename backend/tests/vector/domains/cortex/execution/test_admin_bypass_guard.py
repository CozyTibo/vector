"""Wave 4 — admin bypass route burial CI guard."""

from __future__ import annotations

from vector.domains.cortex.execution.admin_bypass_guard import (
    verify_no_admin_bypass_routes_registered_v1,
)
from vector.domains.cortex.execution.scheduling import verify_m8_admin_execution_surface_v1


def test_verify_no_admin_bypass_routes_registered() -> None:
    assert verify_no_admin_bypass_routes_registered_v1() == []


def test_m8_surface_includes_bypass_guard() -> None:
    assert verify_m8_admin_execution_surface_v1() == []
