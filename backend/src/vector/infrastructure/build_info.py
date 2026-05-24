"""Deploy/build identity surfaced to operators (Settings footer, health probes)."""

from __future__ import annotations

import os
from typing import Any

from vector.settings import Settings


def resolve_deploy_git_sha(*, settings: Settings | None = None) -> str | None:
    """Return the git SHA baked into this deployment, if configured."""
    if settings is not None:
        configured = (getattr(settings, "vector_git_sha", None) or "").strip()
        if configured:
            return configured
    env_val = os.environ.get("VECTOR_GIT_SHA", "").strip()
    return env_val or None


def build_deploy_info_payload(*, settings: Settings) -> dict[str, Any]:
    git_sha = resolve_deploy_git_sha(settings=settings)
    return {
        "surface_kind": "admin_build_info",
        "git_sha": git_sha,
        "git_sha_short": git_sha[:7] if git_sha else None,
        "cortex_admin_v2_enabled": bool(settings.cortex_admin_v2),
        "env": settings.env,
    }
