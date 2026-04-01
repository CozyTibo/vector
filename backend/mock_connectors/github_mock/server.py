"""GitHub mock HTTP — router factory."""

from __future__ import annotations

from typing import Any

from mock_connectors.github_mock.routes.rest import build_github_router

__all__ = ["build_github_router"]


def create_app_router(gh: dict[str, Any]) -> Any:
    return build_github_router(gh)
