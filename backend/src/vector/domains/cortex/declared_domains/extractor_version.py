"""Declared domains projection version."""

from __future__ import annotations

DECLARED_DOMAIN_EXTRACTOR_VERSION = 1


def effective_declared_domain_extractor_version(override: int | None) -> int:
    if override is not None and override > 0:
        return int(override)
    return DECLARED_DOMAIN_EXTRACTOR_VERSION
