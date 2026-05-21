"""M8 static verification — admin execution surface."""

from vector.domains.cortex.execution.scheduling import verify_m8_admin_execution_surface_v1


def test_m8_admin_execution_surface_static() -> None:
    assert verify_m8_admin_execution_surface_v1() == []
