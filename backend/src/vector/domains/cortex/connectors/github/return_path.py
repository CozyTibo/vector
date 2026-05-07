"""Validate post-install redirect paths (avoid open redirects)."""

from __future__ import annotations


def sanitize_github_install_return_to(raw: str | None) -> str | None:
    """Allow only same-origin app paths like ``/app/onboarding``."""
    if raw is None:
        return None
    s = raw.strip()
    if not s.startswith("/") or s.startswith("//"):
        return None
    if "://" in s:
        return None
    if not s.startswith("/app/"):
        return None
    base = s.split("?", 1)[0].split("#", 1)[0]
    if not base.startswith("/app/"):
        return None
    return base or None
