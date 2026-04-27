"""Registered connector behavior (no FastAPI — safe for domain layer)."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy.orm import Session

from vector.contracts.connectors import ConnectorStatusItem
from vector.settings import Settings


@dataclass(frozen=True, slots=True)
class ConnectorRuntime:
    """Hooks for list/disconnect; HTTP mounts live under api/http/routes/connectors/."""

    id: str
    display_name: str
    status_for_tenant: Callable[[Session, Settings, uuid.UUID], ConnectorStatusItem]
    disconnect_tenant: Callable[[Session, uuid.UUID], None]


@lru_cache
def connector_runtimes() -> tuple[ConnectorRuntime, ...]:
    """All built-in providers. Import adapters inside to avoid circular imports."""
    from vector.domains.connectors.calls.adapter import calls_connector_runtime
    from vector.domains.connectors.github.adapter import github_connector_runtime
    from vector.domains.connectors.linear.adapter import linear_connector_runtime
    from vector.domains.connectors.notion.adapter import notion_connector_runtime
    from vector.domains.connectors.slack.adapter import slack_connector_runtime

    return (
        calls_connector_runtime(),
        github_connector_runtime(),
        linear_connector_runtime(),
        notion_connector_runtime(),
        slack_connector_runtime(),
    )


def runtime_by_id() -> dict[str, ConnectorRuntime]:
    return {r.id: r for r in connector_runtimes()}


def all_runtimes_ordered() -> Sequence[ConnectorRuntime]:
    return tuple(sorted(connector_runtimes(), key=lambda r: r.id))
