"""Phase 01 Step 6 — operator pause for Beat-driven Cortex ingestion (global, Redis-backed).

When ``REDIS_URL`` is set, Beat's scheduler tick consults this flag before enqueueing live-lane
tasks. Env ``CORTEX_INGESTION_SCHEDULER_ENABLED`` remains the primary on/off switch; this layer is
an operational brake that does not require a process restart.
"""

from __future__ import annotations

import logging
from typing import Final

import redis

from vector.infrastructure.redis_url import normalize_rediss_url
from vector.settings import Settings

_LOGGER = logging.getLogger("app")

_REDIS_KEY: Final[str] = "vector:cortex_ingestion:scheduler_paused"


def scheduler_pause_redis_available(settings: Settings) -> bool:
    return bool(settings.redis_url.strip())


def read_scheduler_paused_flag(settings: Settings) -> bool:
    """Return True when operators requested a pause via Redis (fail open on errors)."""
    if not scheduler_pause_redis_available(settings):
        return False
    try:
        client = redis.Redis.from_url(
            normalize_rediss_url(settings.redis_url),
            decode_responses=True,
        )
        with client:
            return client.get(_REDIS_KEY) == "1"
    except Exception:
        _LOGGER.warning(
            "cortex scheduler pause read failed; treating as not paused",
            exc_info=True,
        )
        return False


def write_scheduler_paused_flag(settings: Settings, *, paused: bool) -> None:
    """Persist pause flag in Redis (raises if Redis is unavailable)."""
    if not scheduler_pause_redis_available(settings):
        msg = "REDIS_URL is not configured; scheduler pause is unavailable in this deployment."
        raise RuntimeError(msg)
    client = redis.Redis.from_url(
        normalize_rediss_url(settings.redis_url),
        decode_responses=True,
    )
    with client:
        if paused:
            client.set(_REDIS_KEY, "1")
        else:
            client.delete(_REDIS_KEY)
