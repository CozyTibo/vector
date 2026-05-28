"""Bump when deterministic identity resolver behavior changes."""

from __future__ import annotations

import os

IDENTITY_RESOLVER_VERSION = 1


def get_identity_resolver_version(override: int | None = None) -> int:
    if override is not None:
        return max(1, int(override))
    raw = os.environ.get("CORTEX_IDENTITY_RESOLVER_VERSION", "").strip()
    if not raw:
        return IDENTITY_RESOLVER_VERSION
    try:
        v = int(raw)
    except ValueError:
        return IDENTITY_RESOLVER_VERSION
    return max(1, v)

