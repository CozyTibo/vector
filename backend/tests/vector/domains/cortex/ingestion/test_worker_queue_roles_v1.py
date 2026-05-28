"""ECS worker queue bindings — ingestion vs dedicated canon lane."""

from vector.domains.cortex.ingestion.worker_queue_roles_v1 import (
    CELERY_CANON_QUEUES_V1,
    CELERY_IDENTITY_QUEUES_V1,
    CELERY_INGESTION_QUEUES_V1,
    apply_canon_worker_task_definition_v1,
    apply_identity_worker_task_definition_v1,
    apply_ingestion_worker_task_definition_v1,
    apply_substrate_worker_task_definition_v1,
    canon_worker_command_v1,
    identity_worker_command_v1,
    ingestion_worker_command_v1,
)


def test_ingestion_worker_queues_exclude_cortex_canon() -> None:
    assert "cortex_canon" not in CELERY_INGESTION_QUEUES_V1
    cmd = ingestion_worker_command_v1()
    q_idx = cmd.index("-Q")
    assert cmd[q_idx + 1] == "cortex_live,cortex_replay"


def test_canon_worker_queues_only_cortex_canon() -> None:
    assert CELERY_CANON_QUEUES_V1 == ("cortex_canon",)
    cmd = canon_worker_command_v1()
    q_idx = cmd.index("-Q")
    assert cmd[q_idx + 1] == "cortex_canon"


def test_identity_worker_queues_only_cortex_identity() -> None:
    assert CELERY_IDENTITY_QUEUES_V1 == ("cortex_identity",)
    cmd = identity_worker_command_v1()
    q_idx = cmd.index("-Q")
    assert cmd[q_idx + 1] == "cortex_identity"


def test_canon_task_def_single_container_without_beat() -> None:
    task_def = {
        "containerDefinitions": [
            {"name": "worker", "image": "img:1", "command": ["old"]},
            {"name": "celery-beat", "image": "img:1", "command": ["beat"]},
        ],
    }
    out = apply_canon_worker_task_definition_v1(task_def)
    assert len(out["containerDefinitions"]) == 1
    assert out["containerDefinitions"][0]["name"] == "worker"
    assert "cortex_canon" in out["containerDefinitions"][0]["command"][-1]


def test_ingestion_and_identity_task_defs_drop_beat_sidecar() -> None:
    task_def = {
        "containerDefinitions": [
            {"name": "worker", "image": "img:1", "command": ["old"]},
            {"name": "celery-beat", "image": "img:1", "command": ["beat"]},
        ],
    }
    ingestion = apply_ingestion_worker_task_definition_v1(task_def)
    identity = apply_identity_worker_task_definition_v1(task_def)
    assert len(ingestion["containerDefinitions"]) == 1
    assert len(identity["containerDefinitions"]) == 1
    assert "cortex_live" in ingestion["containerDefinitions"][0]["command"][-1]
    assert "cortex_identity" in identity["containerDefinitions"][0]["command"][-1]


def test_substrate_task_def_keeps_beat_sidecar() -> None:
    task_def = {
        "containerDefinitions": [
            {"name": "worker", "image": "img:1", "command": ["old"]},
            {"name": "celery-beat", "image": "img:1", "command": ["beat"]},
        ],
    }
    out = apply_substrate_worker_task_definition_v1(task_def)
    assert len(out["containerDefinitions"]) == 2
    assert out["containerDefinitions"][0]["command"][-1] == "vector"
