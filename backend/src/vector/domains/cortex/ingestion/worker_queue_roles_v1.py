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


def _single_worker_container_task_definition_v1(
    task_def: dict[str, Any],
    *,
    command: list[str],
) -> dict[str, Any]:
    """Drop celery-beat sidecars — only one Beat container may run per cluster."""
    out = dict(task_def)
    container = _worker_container_from_task_def(task_def)
    container["command"] = command
    out["containerDefinitions"] = [container]
    return out


def apply_canon_worker_task_definition_v1(
    task_def: dict[str, Any],
    *,
    concurrency: int = 2,
) -> dict[str, Any]:
    """Single-container task def for canon-only worker (no Beat sidecar)."""
    return _single_worker_container_task_definition_v1(
        task_def,
        command=canon_worker_command_v1(concurrency=concurrency),
    )


def apply_ingestion_worker_task_definition_v1(
    task_def: dict[str, Any],
    *,
    concurrency: int = 2,
) -> dict[str, Any]:
    """Ingestion lane worker only (Beat runs on the substrate/vector-queue service)."""
    return _single_worker_container_task_definition_v1(
        task_def,
        command=ingestion_worker_command_v1(concurrency=concurrency),
    )


def apply_identity_worker_task_definition_v1(
    task_def: dict[str, Any],
    *,
    concurrency: int = 2,
) -> dict[str, Any]:
    """Identity lane worker only (Beat runs on the substrate/vector-queue service)."""
    return _single_worker_container_task_definition_v1(
        task_def,
        command=identity_worker_command_v1(concurrency=concurrency),
    )


def apply_substrate_worker_task_definition_v1(
    task_def: dict[str, Any],
    *,
    concurrency: int = 2,
) -> dict[str, Any]:
    """Substrate/vector-queue worker; retains celery-beat sidecar when present."""
    out = dict(task_def)
    containers = [dict(c) for c in out.get("containerDefinitions") or []]
    if not containers:
        msg = "task definition has no containerDefinitions"
        raise ValueError(msg)
    worker = _worker_container_from_task_def(task_def)
    worker["command"] = substrate_worker_command_v1(concurrency=concurrency)
    replaced = False
    for i, raw in enumerate(containers):
        if raw.get("name") == "worker" or (not replaced and raw.get("name") != "celery-beat"):
            containers[i] = worker
            replaced = True
            break
    if not replaced:
        containers[0] = worker
    out["containerDefinitions"] = containers
    return out


def apply_worker_role_to_task_definition_v1(
    task_def: dict[str, Any],
    *,
    role: str,
    concurrency: int = 2,
) -> dict[str, Any]:
    """Return a copy of an ECS task definition with Celery ``command`` for a worker role."""
    if role == "ingestion":
        return apply_ingestion_worker_task_definition_v1(task_def, concurrency=concurrency)
    if role == "substrate":
        return apply_substrate_worker_task_definition_v1(task_def, concurrency=concurrency)
    if role == "canon":
        return apply_canon_worker_task_definition_v1(task_def, concurrency=concurrency)
    if role == "identity":
        return apply_identity_worker_task_definition_v1(task_def, concurrency=concurrency)
    msg = f"unsupported_worker_role:{role}"
    raise ValueError(msg)
