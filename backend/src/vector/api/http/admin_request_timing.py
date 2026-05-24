"""Structured duration logging for hot admin cortex endpoints."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

_LOGGER = logging.getLogger("app.admin_timing")


@contextmanager
def admin_request_timing(
    *,
    endpoint: str,
    tenant_id: uuid.UUID | None = None,
    **extra: Any,
) -> Iterator[None]:
    """Log wall time for an admin handler (bootstrap, semantic-readiness, etc.)."""
    started = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - started) * 1000.0
        fields: dict[str, Any] = {
            "endpoint": endpoint,
            "duration_ms": round(duration_ms, 1),
        }
        if tenant_id is not None:
            fields["tenant_id"] = str(tenant_id)
        fields.update(extra)
        _LOGGER.info("admin_request_timing %s", " ".join(f"{k}={v!r}" for k, v in fields.items()))
