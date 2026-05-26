"""Worker queue role split — ingestion vs substrate Celery queues."""

from __future__ import annotations

from vector.domains.cortex.execution.worker_queue_roles_v1 import (
    apply_worker_role_to_task_definition_v1,
    ingestion_worker_command_v1,
    substrate_worker_command_v1,
)


def test_ingestion_worker_command_excludes_vector_queue() -> None:
    cmd = ingestion_worker_command_v1()
    assert "-Q" in cmd
    q = cmd[cmd.index("-Q") + 1]
    assert "vector" not in q.split(",")
    assert "cortex_live" in q


def test_substrate_worker_command_vector_only() -> None:
    cmd = substrate_worker_command_v1()
    q = cmd[cmd.index("-Q") + 1]
    assert q == "vector"


def test_apply_worker_role_to_task_definition() -> None:
    base = {
        "family": "vector-backend-worker",
        "containerDefinitions": [{"name": "worker", "image": "img:latest", "command": ["old"]}],
    }
    ing = apply_worker_role_to_task_definition_v1(base, role="ingestion")
    sub = apply_worker_role_to_task_definition_v1(base, role="substrate")
    assert "cortex_live" in ing["containerDefinitions"][0]["command"][-1]
    assert sub["containerDefinitions"][0]["command"][-1] == "vector"
