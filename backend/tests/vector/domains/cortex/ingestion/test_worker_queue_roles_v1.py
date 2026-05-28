"""ECS worker queue bindings — two-service model (ingestion + cortex)."""

from vector.domains.cortex.ingestion.worker_queue_roles_v1 import (
    CELERY_CORTEX_QUEUES_V1,
    CELERY_INGESTION_QUEUES_V1,
    apply_cortex_worker_task_definition_v1,
    apply_ingestion_worker_task_definition_v1,
    cortex_worker_command_v1,
    ingestion_worker_command_v1,
)


def test_ingestion_worker_queues_exclude_pass_lanes() -> None:
    assert "cortex_canon" not in CELERY_INGESTION_QUEUES_V1
    cmd = ingestion_worker_command_v1()
    q_idx = cmd.index("-Q")
    assert cmd[q_idx + 1] == "cortex_live,cortex_replay"


def test_cortex_worker_queues_include_ticks_and_passes() -> None:
    assert CELERY_CORTEX_QUEUES_V1 == ("vector", "cortex_canon", "cortex_identity")
    cmd = cortex_worker_command_v1()
    q_idx = cmd.index("-Q")
    assert cmd[q_idx + 1] == "vector,cortex_canon,cortex_identity"


def test_ingestion_task_def_single_container_without_beat() -> None:
    task_def = {
        "containerDefinitions": [
            {"name": "worker", "image": "img:1", "command": ["old"]},
            {"name": "celery-beat", "image": "img:1", "command": ["beat"]},
        ],
    }
    out = apply_ingestion_worker_task_definition_v1(task_def)
    assert len(out["containerDefinitions"]) == 1
    assert "cortex_live" in out["containerDefinitions"][0]["command"][-1]


def test_cortex_task_def_keeps_beat_sidecar() -> None:
    task_def = {
        "containerDefinitions": [
            {"name": "worker", "image": "img:1", "command": ["old"]},
            {"name": "celery-beat", "image": "img:1", "command": ["beat"]},
        ],
    }
    out = apply_cortex_worker_task_definition_v1(task_def)
    assert len(out["containerDefinitions"]) == 2
    assert "cortex_canon" in out["containerDefinitions"][0]["command"][-1]
