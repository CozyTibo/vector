"""Redis-backed reservations for tenant×connector work already on ``cortex_live``.

The Beat scheduler sets a key before ``apply_async``; ingestion workers clear it when
``run_sync`` finishes. This prevents duplicate enqueue while a message is still in the broker
(not only when Postgres shows ``RUNNING``).
"""

from __future__ import annotations

import logging
import uuid
from typing import Final

import redis

from vector.infrastructure.cortex_scheduler_pause import scheduler_pause_redis_available
from vector.infrastructure.redis_url import normalize_rediss_url
from vector.settings import Settings

_LOGGER = logging.getLogger(__name__)

_KEY_PREFIX: Final[str] = "vector:cortex_live:pending"


def _redis_key(*, tenant_id: uuid.UUID, connection_id: uuid.UUID) -> str:
    return f"{_KEY_PREFIX}:{tenant_id}:{connection_id}"


def _pending_ttl_seconds(settings: Settings) -> int:
    return max(300, int(settings.cortex_ingestion_live_pending_ttl_seconds))


def is_live_queue_pending(
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> bool:
    """Return True when a scheduled sync is reserved (broker or worker in flight)."""
    if not scheduler_pause_redis_available(settings):
        return False
    try:
        client = redis.Redis.from_url(
            normalize_rediss_url(settings.redis_url),
            decode_responses=True,
        )
        with client:
            return client.get(_redis_key(tenant_id=tenant_id, connection_id=connection_id)) is not None
    except Exception:
        _LOGGER.warning(
            "cortex live pending read failed; treating as not pending",
            extra={"tenant_id": str(tenant_id), "connection_id": str(connection_id)},
            exc_info=True,
        )
        return False


def reserve_live_queue_pending(
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> bool:
    """Atomically reserve a slot before enqueue; False if already pending."""
    if not scheduler_pause_redis_available(settings):
        return True
    try:
        client = redis.Redis.from_url(
            normalize_rediss_url(settings.redis_url),
            decode_responses=True,
        )
        with client:
            return bool(
                client.set(
                    _redis_key(tenant_id=tenant_id, connection_id=connection_id),
                    "1",
                    nx=True,
                    ex=_pending_ttl_seconds(settings),
                ),
            )
    except Exception:
        _LOGGER.warning(
            "cortex live pending reserve failed; allowing enqueue",
            extra={"tenant_id": str(tenant_id), "connection_id": str(connection_id)},
            exc_info=True,
        )
        return True


def clear_live_queue_pending(
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> None:
    """Release reservation after ``run_sync`` completes, fails, or skips."""
    if not scheduler_pause_redis_available(settings):
        return
    try:
        client = redis.Redis.from_url(
            normalize_rediss_url(settings.redis_url),
            decode_responses=True,
        )
        with client:
            client.delete(_redis_key(tenant_id=tenant_id, connection_id=connection_id))
    except Exception:
        _LOGGER.warning(
            "cortex live pending clear failed",
            extra={"tenant_id": str(tenant_id), "connection_id": str(connection_id)},
            exc_info=True,
        )
