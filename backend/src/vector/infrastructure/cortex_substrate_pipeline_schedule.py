"""Coalesce post-ingestion substrate pipeline Celery schedules (debounce without starvation).

Each incremental sync used to ``revoke`` + ``apply_async`` the same ``task_id``, resetting the
countdown forever while ingestion stays hot. We preserve one pending coordinator until either it
fires or ``max_wait_seconds`` elapses (then force ``countdown=0``).
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Final, Literal

import redis

from vector.infrastructure.redis_url import normalize_rediss_url
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)

ScheduleAction = Literal["schedule", "coalesce", "force_now"]

_REDIS_KEY_PREFIX: Final[str] = "vector:cortex:substrate_pipeline:schedule_anchor:"


def _anchor_key(tenant_id: uuid.UUID | str) -> str:
    return f"{_REDIS_KEY_PREFIX}{tenant_id}"


def substrate_pipeline_schedule_redis_available(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    return bool(cfg.redis_url.strip())


def read_substrate_pipeline_schedule_anchor_v1(
    tenant_id: uuid.UUID | str,
    *,
    settings: Settings | None = None,
) -> float | None:
    """Unix timestamp when the current debounce window started, or None."""
    cfg = settings or get_settings()
    if not substrate_pipeline_schedule_redis_available(cfg):
        return None
    try:
        client = redis.Redis.from_url(
            normalize_rediss_url(cfg.redis_url),
            decode_responses=True,
        )
        with client:
            raw = client.get(_anchor_key(tenant_id))
        if raw is None:
            return None
        return float(raw)
    except Exception:
        _LOGGER.warning(
            "substrate pipeline schedule anchor read failed tenant_id=%s",
            tenant_id,
            exc_info=True,
        )
        return None


def write_substrate_pipeline_schedule_anchor_v1(
    tenant_id: uuid.UUID | str,
    *,
    anchor_unix: float | None = None,
    ttl_seconds: int,
    settings: Settings | None = None,
) -> bool:
    """Set anchor if missing (NX). Returns True when written."""
    cfg = settings or get_settings()
    if not substrate_pipeline_schedule_redis_available(cfg):
        return False
    ts = anchor_unix if anchor_unix is not None else time.time()
    try:
        client = redis.Redis.from_url(
            normalize_rediss_url(cfg.redis_url),
            decode_responses=True,
        )
        with client:
            return bool(
                client.set(
                    _anchor_key(tenant_id),
                    str(ts),
                    nx=True,
                    ex=max(60, int(ttl_seconds)),
                )
            )
    except Exception:
        _LOGGER.warning(
            "substrate pipeline schedule anchor write failed tenant_id=%s",
            tenant_id,
            exc_info=True,
        )
        return False


def clear_substrate_pipeline_schedule_anchor_v1(
    tenant_id: uuid.UUID | str,
    *,
    settings: Settings | None = None,
) -> None:
    cfg = settings or get_settings()
    if not substrate_pipeline_schedule_redis_available(cfg):
        return
    try:
        client = redis.Redis.from_url(
            normalize_rediss_url(cfg.redis_url),
            decode_responses=True,
        )
        with client:
            client.delete(_anchor_key(tenant_id))
    except Exception:
        _LOGGER.warning(
            "substrate pipeline schedule anchor clear failed tenant_id=%s",
            tenant_id,
            exc_info=True,
        )


def resolve_substrate_pipeline_schedule_action_v1(
    tenant_id: uuid.UUID | str,
    *,
    debounce_seconds: int,
    max_wait_seconds: int,
    settings: Settings | None = None,
) -> tuple[ScheduleAction, dict[str, object]]:
    """Decide whether to enqueue, preserve pending coordinator, or force immediate run."""
    cfg = settings or get_settings()
    now = time.time()
    anchor = read_substrate_pipeline_schedule_anchor_v1(tenant_id, settings=cfg)
    meta: dict[str, object] = {
        "anchor_unix": anchor,
        "now_unix": now,
        "debounce_seconds": debounce_seconds,
        "max_wait_seconds": max_wait_seconds,
    }
    if anchor is None:
        return "schedule", meta

    elapsed = now - anchor
    meta["elapsed_seconds"] = elapsed
    if elapsed >= max(1, int(max_wait_seconds)):
        return "force_now", meta
    return "coalesce", meta
