"""Admin API builder for semantic readiness (Wave S0)."""

from __future__ import annotations

import copy
import threading
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.semantic_readiness_v1 import (
    build_semantic_readiness_v1,
)
from vector.settings import Settings

_SEMANTIC_CACHE_LOCK = threading.Lock()
_SEMANTIC_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_SEMANTIC_CACHE_TTL_SECONDS = 60.0


def invalidate_semantic_readiness_cache_v1(tenant_id: uuid.UUID) -> None:
    with _SEMANTIC_CACHE_LOCK:
        _SEMANTIC_CACHE.pop(str(tenant_id), None)


def build_semantic_readiness_admin_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Cached semantic readiness for admin surfaces."""
    del settings
    key = str(tenant_id)
    now = time.monotonic()
    with _SEMANTIC_CACHE_LOCK:
        hit = _SEMANTIC_CACHE.get(key)
        if hit is not None and (now - hit[0]) < _SEMANTIC_CACHE_TTL_SECONDS:
            return copy.deepcopy(hit[1])
    payload = build_semantic_readiness_v1(session, tenant_id=tenant_id)
    with _SEMANTIC_CACHE_LOCK:
        _SEMANTIC_CACHE[key] = (now, copy.deepcopy(payload))
    return payload
