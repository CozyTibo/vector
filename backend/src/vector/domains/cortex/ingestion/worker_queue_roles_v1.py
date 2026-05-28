"""ECS Celery worker queue roles — ingestion lane + merged cortex lane."""

from __future__ import annotations

from typing import Any, Final

# Ingestion lane: connector sync only (I/O bound; isolated from pass CPU).
CELERY_INGESTION_QUEUES_V1: Final[tuple[str, ...]] = (
    "cortex_live",
    "cortex_replay",
)
# Cortex lane: Beat ticks, email, and DB-backed pass execution (canon + identity).
CELERY_CORTEX_QUEUES_V1: Final[tuple[str, ...]] = (
    "vector",
    "cortex_canon",
    "cortex_identity",
)

# Legacy aliases (tests / scripts).
CELERY_CANON_QUEUES_V1: Final[tuple[str, ...]] = ("cortex_canon",)
CELERY_IDENTITY_QUEUES_V1: Final[tuple[str, ...]] = ("cortex_identity",)
CELERY_DEFAULT_WORKER_QUEUES_V1: Final[tuple[str, ...]] = ("vector",)
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


def cortex_worker_command_v1(*, concurrency: int = 3) -> list[str]:
    """Merged cortex worker: scheduler ticks + pass execution queues."""
    return celery_worker_command_for_queues_v1(
        queues=CELERY_CORTEX_QUEUES_V1,
        concurrency=concurrency,
        prefetch_multiplier=1,
    )


def substrate_worker_command_v1(*, concurrency: int = 3) -> list[str]:
    """Alias for cortex worker (ECS service name still vector-substrate-worker)."""
    return cortex_worker_command_v1(concurrency=concurrency)


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


def apply_ingestion_worker_task_definition_v1(
    task_def: dict[str, Any],
    *,
    concurrency: int = 2,
) -> dict[str, Any]:
    """Ingestion lane worker only (Beat runs on the cortex worker service)."""
    return _single_worker_container_task_definition_v1(
        task_def,
        command=ingestion_worker_command_v1(concurrency=concurrency),
    )


def apply_cortex_worker_task_definition_v1(
    task_def: dict[str, Any],
    *,
    concurrency: int = 3,
) -> dict[str, Any]:
    """Cortex worker; retains celery-beat sidecar when present."""
    out = dict(task_def)
    containers = [dict(c) for c in out.get("containerDefinitions") or []]
    if not containers:
        msg = "task definition has no containerDefinitions"
        raise ValueError(msg)
    worker = _worker_container_from_task_def(task_def)
    worker["command"] = cortex_worker_command_v1(concurrency=concurrency)
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


def apply_substrate_worker_task_definition_v1(
    task_def: dict[str, Any],
    *,
    concurrency: int = 3,
) -> dict[str, Any]:
    return apply_cortex_worker_task_definition_v1(task_def, concurrency=concurrency)


def apply_worker_role_to_task_definition_v1(
    task_def: dict[str, Any],
    *,
    role: str,
    concurrency: int = 2,
) -> dict[str, Any]:
    """Return a copy of an ECS task definition with Celery ``command`` for a worker role."""
    if role == "ingestion":
        return apply_ingestion_worker_task_definition_v1(task_def, concurrency=concurrency)
    if role in ("substrate", "cortex"):
        return apply_cortex_worker_task_definition_v1(
            task_def,
            concurrency=max(concurrency, 3),
        )
    msg = f"unsupported_worker_role:{role}"
    raise ValueError(msg)
