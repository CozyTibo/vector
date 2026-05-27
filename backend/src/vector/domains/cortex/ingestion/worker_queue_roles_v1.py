"""ECS Celery worker queue roles — ingestion vs default (Beat + misc tasks)."""

from __future__ import annotations

from typing import Any, Final

# Ingestion lane: connector sync (high volume).
CELERY_INGESTION_QUEUES_V1: Final[tuple[str, ...]] = ("cortex_live", "cortex_replay")
# Default lane: Beat scheduler tick, email, onboarding, verify (must not starve behind sync).
CELERY_DEFAULT_WORKER_QUEUES_V1: Final[tuple[str, ...]] = ("vector",)

# Deploy scripts still use role name "substrate" for the vector-queue worker service.
CELERY_SUBSTRATE_QUEUES_V1 = CELERY_DEFAULT_WORKER_QUEUES_V1

CELERY_WORKER_BASE_CMD_V1: Final[list[str]] = [
    "celery",
    "-A",
    "app.worker",
    "worker",
    "--loglevel",
    "info",
]


def celery_worker_command_for_queues_v1(
    *,
    queues: tuple[str, ...],
    concurrency: int = 2,
    prefetch_multiplier: int = 1,
) -> list[str]:
    q = ",".join(queues)
    return [
        *CELERY_WORKER_BASE_CMD_V1,
        "--concurrency",
        str(max(1, min(concurrency, 8))),
        f"--prefetch-multiplier={max(1, min(prefetch_multiplier, 4))}",
        "-Q",
        q,
    ]


def ingestion_worker_command_v1(*, concurrency: int = 2) -> list[str]:
    return celery_worker_command_for_queues_v1(
        queues=CELERY_INGESTION_QUEUES_V1,
        concurrency=concurrency,
        prefetch_multiplier=1,
    )


def substrate_worker_command_v1(*, concurrency: int = 2) -> list[str]:
    return celery_worker_command_for_queues_v1(
        queues=CELERY_SUBSTRATE_QUEUES_V1,
        concurrency=concurrency,
        prefetch_multiplier=1,
    )


def apply_worker_role_to_task_definition_v1(
    task_def: dict[str, Any],
    *,
    role: str,
    concurrency: int = 2,
) -> dict[str, Any]:
    """Return a copy of an ECS task definition with Celery ``command`` for ``ingestion`` or ``substrate`` role."""
    out = dict(task_def)
    containers = list(out.get("containerDefinitions") or [])
    if not containers:
        return out
    container = dict(containers[0])
    if role == "ingestion":
        container["command"] = ingestion_worker_command_v1(concurrency=concurrency)
    elif role == "substrate":
        container["command"] = substrate_worker_command_v1(concurrency=concurrency)
    else:
        msg = f"unsupported_worker_role:{role}"
        raise ValueError(msg)
    containers[0] = container
    out["containerDefinitions"] = containers
    return out
