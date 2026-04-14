"""Shared checks before polling mock connector HTTP APIs (local dev)."""

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, status

from vector.settings import Settings

_logger = logging.getLogger("app")


def _docker_loopback_hint(url: str) -> str:
    """Extra guidance when health URL uses loopback — often wrong from inside Docker."""
    u = url.lower()
    if "127.0.0.1" not in u and "localhost" not in u:
        return ""
    return (
        " If the Vector API runs in Docker, 127.0.0.1/localhost is the container, not your "
        "machine — set VECTOR_MOCK_CONNECTOR_BASE_URL=http://host.docker.internal:9183 in `.env` "
        "(mock stays on the host; restart the backend). On Linux you may need "
        "`extra_hosts: [\"host.docker.internal:host-gateway\"]` in Compose."
    )


def preflight_mock_connectors_reachable(settings: Settings) -> None:
    """No-op unless mock mode; then GET {mock_base}/health must succeed."""
    if not settings.vector_use_mock_connectors:
        return
    base = settings.github_rest_api_base_url().rstrip("/")
    url = f"{base}/health"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except Exception as exc:
        _logger.warning("mock connectors health check failed: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Local mock connectors are not reachable at {url}. "
                "With Docker Compose, run `docker compose up` (service `mock-connectors`). "
                "Otherwise: `make -f Makefile.mock mock-connectors-up` "
                "(see backend/mock_connectors/README.md)."
                f"{_docker_loopback_hint(url)}"
            ),
        ) from exc
