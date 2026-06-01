"""Per-tenant lock while clear-derived is running (blocks pass planning/execution)."""

from __future__ import annotations

import logging
import uuid

import redis

from vector.infrastructure.cortex_scheduler_pause import scheduler_pause_redis_available
from vector.infrastructure.redis_url import normalize_rediss_url
from vector.settings import Settings

_LOGGER = logging.getLogger(__name__)

_REDIS_KEY_PREFIX = "vector:cortex:clear_derived:"
_TTL_SECONDS = 3600


def _redis_key(tenant_id: uuid.UUID) -> str:
    return f"{_REDIS_KEY_PREFIX}{tenant_id}"


def tenant_clear_derived_in_progress(settings: Settings, tenant_id: uuid.UUID) -> bool:
    if not scheduler_pause_redis_available(settings):
        return False
    try:
        client = redis.Redis.from_url(
            normalize_rediss_url(settings.redis_url),
            decode_responses=True,
        )
        with client:
            return client.get(_redis_key(tenant_id)) == "1"
    except Exception:
        _LOGGER.warning(
            "clear_derived lock read failed; treating as not locked",
            extra={"tenant_id": str(tenant_id)},
            exc_info=True,
        )
        return False


def set_tenant_clear_derived_in_progress(
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    active: bool,
) -> None:
    if not scheduler_pause_redis_available(settings):
        return
    client = redis.Redis.from_url(
        normalize_rediss_url(settings.redis_url),
        decode_responses=True,
    )
    with client:
        key = _redis_key(tenant_id)
        if active:
            client.setex(key, _TTL_SECONDS, "1")
        else:
            client.delete(key)
