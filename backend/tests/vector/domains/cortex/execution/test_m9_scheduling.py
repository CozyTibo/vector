"""M9: dead Celery sidecar modules and phase-runner hooks must stay removed."""

from vector.domains.cortex.execution.scheduling import (
    verify_m9_dead_celery_modules_absent_v1,
)


def test_m9_dead_celery_modules_absent() -> None:
    assert verify_m9_dead_celery_modules_absent_v1() == []
