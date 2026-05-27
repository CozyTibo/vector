"""ECS worker queue bindings include canon materialization lane."""

from vector.domains.cortex.ingestion.worker_queue_roles_v1 import (
    CELERY_INGESTION_QUEUES_V1,
    ingestion_worker_command_v1,
)


def test_ingestion_worker_queues_include_cortex_canon() -> None:
    assert "cortex_canon" in CELERY_INGESTION_QUEUES_V1
    cmd = ingestion_worker_command_v1()
    q_idx = cmd.index("-Q")
    assert "cortex_canon" in cmd[q_idx + 1]
