"""Tenant slug derivation (pure)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable


def base_slug_from_domain(domain: str) -> str:
    """ASCII-ish slug from email domain; never empty."""
    raw = domain.lower().strip(". ")
    cleaned = re.sub(r"[^a-z0-9]+", "-", raw)
    out = cleaned.strip("-")
    return out if out else "org"


def unique_slug(session_fetch_first: Callable[[str], object | None], domain: str) -> str:
    """
    Unique slug: base from domain, append short suffix on collision.

    session_fetch_first(slug: str) -> row | None
    """
    base = base_slug_from_domain(domain)
    if session_fetch_first(base) is None:
        return base
    suffix = str(uuid.uuid4())[:8]
    return f"{base}-{suffix}"
