"""Operator pause flags per Cortex lane (Redis-backed)."""

from __future__ import annotations

import logging
from typing import Final

import redis

from vector.infrastructure.cortex_scheduler_pause import scheduler_pause_redis_available
from vector.infrastructure.redis_url import normalize_rediss_url
from vector.settings import Settings

_LOGGER = logging.getLogger("app")

_LANE_KEYS: Final[dict[str, str]] = {
    "ingestion": "vector:cortex_ingestion:scheduler_paused",
    "canon": "vector:cortex_canon:scheduler_paused",
    "identity": "vector:cortex_identity:scheduler_paused",
    "graph": "vector:cortex_graph:scheduler_paused",
    "declared_domains": "vector:cortex_declared_domains:scheduler_paused",
    "orchestrator": "vector:cortex_orchestrator:paused",
}


def read_lane_paused_flag(settings: Settings, lane: str) -> bool:
    key = _LANE_KEYS.get(lane)
    if key is None or not scheduler_pause_redis_available(settings):
        return False
    try:
        client = redis.Redis.from_url(
            normalize_rediss_url(settings.redis_url),
            decode_responses=True,
        )
        with client:
            return client.get(key) == "1"
    except Exception:
        _LOGGER.warning("cortex lane pause read failed lane=%s", lane, exc_info=True)
        return False


def write_lane_paused_flag(settings: Settings, *, lane: str, paused: bool) -> None:
    key = _LANE_KEYS.get(lane)
    if key is None:
        msg = f"unknown_lane:{lane}"
        raise ValueError(msg)
    if not scheduler_pause_redis_available(settings):
        msg = "REDIS_URL is not configured; lane pause unavailable."
        raise RuntimeError(msg)
    client = redis.Redis.from_url(
        normalize_rediss_url(settings.redis_url),
        decode_responses=True,
    )
    with client:
        if paused:
            client.set(key, "1")
        else:
            client.delete(key)


def read_all_lane_pause_flags(settings: Settings) -> dict[str, bool]:
    return {lane: read_lane_paused_flag(settings, lane) for lane in _LANE_KEYS}
