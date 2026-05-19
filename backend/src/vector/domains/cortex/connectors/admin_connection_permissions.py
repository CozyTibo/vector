"""Build admin-facing permission reports for tenant connections."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.connection_permissions import (
    ConnectionPermissionSnapshot,
    calls_permission_snapshot,
    github_permission_snapshot_from_installation,
    linear_permission_snapshot,
    notion_permission_snapshot,
    slack_permission_snapshot,
)
from vector.domains.cortex.connectors.github.errors import GitHubApiError
from vector.domains.cortex.connectors.github.http_client import fetch_github_installation
from vector.domains.cortex.connectors.cortex_ingestion_policy import SUPPORTED_CONNECTOR_IDS
from vector.domains.cortex.connectors.provider_keys import (
    CONNECTION_PROVIDER_CALLS,
    CONNECTION_PROVIDER_GITHUB,
    CONNECTION_PROVIDER_LINEAR,
    CONNECTION_PROVIDER_NOTION,
    CONNECTION_PROVIDER_SLACK,
)
from vector.infrastructure.db.repositories import (
    github_connection as gh_repo,
    slack_connection as slack_repo,
)
from vector.settings import Settings


def permission_snapshot_for_provider(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    provider: str,
    connected: bool,
) -> ConnectionPermissionSnapshot | None:
    if provider == CONNECTION_PROVIDER_SLACK:
        link = slack_repo.get_slack_connection_for_tenant(session, tenant_id) if connected else None
        granted = link.detail.scope if link is not None else None
        return slack_permission_snapshot(settings, granted_scope=granted, connected=connected)
    if provider == CONNECTION_PROVIDER_LINEAR:
        return linear_permission_snapshot(connected=connected)
    if provider == CONNECTION_PROVIDER_CALLS:
        return calls_permission_snapshot(connected=connected)
    if provider == CONNECTION_PROVIDER_NOTION:
        return notion_permission_snapshot(connected=connected)
    if provider == CONNECTION_PROVIDER_GITHUB:
        installation_payload: dict[str, object] | None = None
        if connected:
            gh_link = gh_repo.get_github_connection_for_tenant(session, tenant_id)
            if gh_link is not None:
                try:
                    installation_payload = fetch_github_installation(
                        settings,
                        gh_link.detail.installation_id,
                    )
                except GitHubApiError:
                    installation_payload = None
        slug = settings.github_app_slug.strip() or "vector"
        return github_permission_snapshot_from_installation(
            installation_payload,
            connected=connected,
            app_slug=slug,
        )
    return None


def permissions_by_provider_for_tenant(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    active_providers: set[str],
) -> dict[str, ConnectionPermissionSnapshot]:
    out: dict[str, ConnectionPermissionSnapshot] = {}
    for provider in sorted(SUPPORTED_CONNECTOR_IDS):
        snap = permission_snapshot_for_provider(
            session,
            settings,
            tenant_id=tenant_id,
            provider=provider,
            connected=provider in active_providers,
        )
        if snap is not None:
            out[provider] = snap
    return out
