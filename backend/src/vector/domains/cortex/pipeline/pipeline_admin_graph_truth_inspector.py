"""Admin API builder for graph truth inspector (Phase G1)."""

from __future__ import annotations

import copy
import threading
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.pipeline.graph_truth_inspector_v1 import (
    build_graph_truth_inspector_v1,
)
from vector.settings import Settings

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 60.0


def invalidate_graph_truth_inspector_cache_v1(tenant_id: uuid.UUID) -> None:
    key = str(tenant_id)
    with _CACHE_LOCK:
        _CACHE.pop(key, None)
        _CACHE.pop(f"{key}:cc", None)


def build_graph_truth_inspector_admin_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    include_connected_components: bool = False,
) -> dict[str, Any]:
    del settings
    key = f"{tenant_id}:cc" if include_connected_components else str(tenant_id)
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit is not None and (now - hit[0]) < _CACHE_TTL_SECONDS:
            return copy.deepcopy(hit[1])
    payload = build_graph_truth_inspector_v1(
        session,
        tenant_id=tenant_id,
        include_connected_components=include_connected_components,
    )
    with _CACHE_LOCK:
        _CACHE[key] = (now, copy.deepcopy(payload))
    return payload
