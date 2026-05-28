"""ECS Celery worker queue roles — ingestion, canon, identity, and default."""

from __future__ import annotations

from typing import Any, Final

# Ingestion lane: connector sync only (high volume; must not starve canon passes).
CELERY_INGESTION_QUEUES_V1: Final[tuple[str, ...]] = (
    "cortex_live",
    "cortex_replay",
)
# Canon lane: materialization passes only (dedicated ECS service in prod).
CELERY_CANON_QUEUES_V1: Final[tuple[str, ...]] = ("cortex_canon",)
# Identity lane: deterministic identity reconciliation passes only.
CELERY_IDENTITY_QUEUES_V1: Final[tuple[str, ...]] = ("cortex_identity",)
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


def canon_worker_command_v1(*, concurrency: int = 2) -> list[str]:
    return celery_worker_command_for_queues_v1(
        queues=CELERY_CANON_QUEUES_V1,
        concurrency=concurrency,
        prefetch_multiplier=1,
    )


def identity_worker_command_v1(*, concurrency: int = 2) -> list[str]:
    return celery_worker_command_for_queues_v1(
        queues=CELERY_IDENTITY_QUEUES_V1,
        concurrency=concurrency,
        prefetch_multiplier=1,
    )


def substrate_worker_command_v1(*, concurrency: int = 2) -> list[str]:
    return celery_worker_command_for_queues_v1(
        queues=CELERY_SUBSTRATE_QUEUES_V1,
        concurrency=concurrency,
        prefetch_multiplier=1,
    )


def _worker_container_from_task_def(task_def: dict[str, Any]) -> dict[str, Any]:
    containers = list(task_def.get("containerDefinitions") or [])
    for raw in containers:
        if raw.get("name") == "worker":
            return dict(raw)
    if containers:
        return dict(containers[0])
    msg = "task definition has no containerDefinitions"
    raise ValueError(msg)


def apply_canon_worker_task_definition_v1(
    task_def: dict[str, Any],
    *,
    concurrency: int = 2,
) -> dict[str, Any]:
    """Single-container task def for canon-only worker (no Beat sidecar)."""
    out = dict(task_def)
    container = _worker_container_from_task_def(task_def)
    container["command"] = canon_worker_command_v1(concurrency=concurrency)
    out["containerDefinitions"] = [container]
    return out


def apply_worker_role_to_task_definition_v1(
    task_def: dict[str, Any],
    *,
    role: str,
    concurrency: int = 2,
) -> dict[str, Any]:
    """Return a copy of an ECS task definition with Celery ``command`` for a worker role."""
    out = dict(task_def)
    containers = list(out.get("containerDefinitions") or [])
    if not containers:
        return out
    container = dict(containers[0])
    if role == "ingestion":
        container["command"] = ingestion_worker_command_v1(concurrency=concurrency)
    elif role == "substrate":
        container["command"] = substrate_worker_command_v1(concurrency=concurrency)
    elif role == "canon":
        return apply_canon_worker_task_definition_v1(task_def, concurrency=concurrency)
    elif role == "identity":
        container["command"] = identity_worker_command_v1(concurrency=concurrency)
    else:
        msg = f"unsupported_worker_role:{role}"
        raise ValueError(msg)
    containers[0] = container
    out["containerDefinitions"] = containers
    return out
