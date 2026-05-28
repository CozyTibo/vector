"""ECS Celery worker queue roles — ingestion lane + merged cortex lane."""

from __future__ import annotations

from typing import Any, Final

# Ingestion lane: connector sync only (I/O bound; isolated from pass CPU).
CELERY_INGESTION_QUEUES_V1: Final[tuple[str, ...]] = (
    "cortex_live",
    "cortex_replay",
)
# Cortex lane: Beat ticks, email, and DB-backed pass poll/plan (vector queue only).
CELERY_CORTEX_QUEUES_V1: Final[tuple[str, ...]] = ("vector",)
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


def cortex_beat_command_v1() -> list[str]:
    """Single-cluster Celery Beat (orchestrator + ingestion schedule)."""
    return ["celery", "-A", "app.worker", "beat", "--loglevel", "info"]


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


def _beat_sidecar_from_worker_v1(worker: dict[str, Any]) -> dict[str, Any]:
    beat: dict[str, Any] = {
        "name": "celery-beat",
        "image": worker.get("image", ""),
        "essential": True,
        "command": cortex_beat_command_v1(),
    }
    for key in ("environment", "secrets", "mountPoints", "volumesFrom", "linuxParameters"):
        if key in worker:
            beat[key] = worker[key]
    log_cfg = worker.get("logConfiguration")
    if isinstance(log_cfg, dict):
        beat_log = dict(log_cfg)
        opts = dict(beat_log.get("options") or {})
        opts["awslogs-stream-prefix"] = "beat"
        beat_log["options"] = opts
        beat["logConfiguration"] = beat_log
    return beat


def apply_cortex_worker_task_definition_v1(
    task_def: dict[str, Any],
    *,
    concurrency: int = 3,
) -> dict[str, Any]:
    """Cortex worker + celery-beat sidecar (Beat injects when missing from source task def)."""
    out = dict(task_def)
    if not out.get("containerDefinitions"):
        msg = "task definition has no containerDefinitions"
        raise ValueError(msg)
    worker = _worker_container_from_task_def(task_def)
    worker["command"] = cortex_worker_command_v1(concurrency=concurrency)

    beat: dict[str, Any] | None = None
    for raw in out.get("containerDefinitions") or []:
        if raw.get("name") == "celery-beat":
            beat = dict(raw)
            beat["command"] = cortex_beat_command_v1()
            if not beat.get("image"):
                beat["image"] = worker.get("image", "")
            break
    if beat is None:
        beat = _beat_sidecar_from_worker_v1(worker)

    out["containerDefinitions"] = [worker, beat]
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
