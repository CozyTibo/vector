"""API payloads for tenant connectors (multi-provider)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class GithubConnectorDetails(BaseModel):
    """GitHub-specific payload when the GitHub connector is connected."""

    model_config = ConfigDict(extra="forbid")

    connection_id: uuid.UUID | None = Field(
        default=None,
        description="tenant_connections.id — use for projection debug and ingestion scope.",
    )
    installation_id: int | None = None
    account_login: str | None = None
    account_type: str | None = None
    last_sync_at: datetime | None = Field(
        default=None,
        description="Legacy per-tool ingestion was removed; this value is always null.",
    )


class GithubConnectorStatusItem(BaseModel):
    """Status row for the GitHub integration."""

    model_config = ConfigDict(extra="forbid")

    provider: Literal["github"] = Field(
        default="github",
        description="Stable id; matches URL segment DELETE /connectors/{provider}.",
    )
    display_name: str = Field(description="Human-readable label for UI.")
    connector_configured: bool = Field(
        description="Server has required credentials/env for this provider.",
    )
    connected: bool = Field(description="Tenant has completed connect for this provider.")
    details: GithubConnectorDetails | None = Field(
        default=None,
        description="Provider-specific data when connected; null otherwise.",
    )


class LinearConnectorDetails(BaseModel):
    """Linear-specific payload when the Linear connector is connected."""

    model_config = ConfigDict(extra="forbid")

    connection_id: uuid.UUID | None = Field(
        default=None,
        description="tenant_connections.id for this Linear link.",
    )
    organization_id: str | None = None
    organization_name: str | None = None
    last_sync_at: datetime | None = Field(
        default=None,
        description="Legacy per-tool ingestion was removed; this value is always null.",
    )


class LinearConnectorStatusItem(BaseModel):
    """Status row for the Linear integration."""

    model_config = ConfigDict(extra="forbid")

    provider: Literal["linear"] = Field(
        default="linear",
        description="Stable id; matches URL segment DELETE /connectors/{provider}.",
    )
    display_name: str = Field(description="Human-readable label for UI.")
    connector_configured: bool = Field(
        description="Server has required credentials/env for this provider.",
    )
    connected: bool = Field(description="Tenant has completed connect for this provider.")
    details: LinearConnectorDetails | None = Field(
        default=None,
        description="Provider-specific data when connected; null otherwise.",
    )


class SlackConnectorDetails(BaseModel):
    """Slack-specific payload when the Slack connector is connected."""

    model_config = ConfigDict(extra="forbid")

    connection_id: uuid.UUID | None = Field(
        default=None,
        description="tenant_connections.id for this Slack link.",
    )
    team_id: str | None = None
    team_name: str | None = None
    last_sync_at: datetime | None = Field(
        default=None,
        description="Legacy per-tool ingestion was removed; this value is always null.",
    )


class SlackConnectorStatusItem(BaseModel):
    """Status row for the Slack integration."""

    model_config = ConfigDict(extra="forbid")

    provider: Literal["slack"] = Field(
        default="slack",
        description="Stable id; matches URL segment DELETE /connectors/{provider}.",
    )
    display_name: str = Field(description="Human-readable label for UI.")
    connector_configured: bool = Field(
        description="Server has required credentials/env for this provider.",
    )
    connected: bool = Field(description="Tenant has completed connect for this provider.")
    details: SlackConnectorDetails | None = Field(
        default=None,
        description="Provider-specific data when connected; null otherwise.",
    )


class NotionConnectorDetails(BaseModel):
    """Notion-specific payload when the Notion connector is connected."""

    model_config = ConfigDict(extra="forbid")

    connection_id: uuid.UUID | None = Field(
        default=None,
        description="tenant_connections.id for this Notion link.",
    )
    workspace_id: str | None = None
    workspace_name: str | None = None
    last_sync_at: datetime | None = Field(
        default=None,
        description="Legacy per-tool ingestion was removed; this value is always null.",
    )


class NotionConnectorStatusItem(BaseModel):
    """Status row for the Notion integration."""

    model_config = ConfigDict(extra="forbid")

    provider: Literal["notion"] = Field(
        default="notion",
        description="Stable id; matches URL segment DELETE /connectors/{provider}.",
    )
    display_name: str = Field(description="Human-readable label for UI.")
    connector_configured: bool = Field(
        description="Server has required credentials/env for this provider.",
    )
    connected: bool = Field(description="Tenant has completed connect for this provider.")
    details: NotionConnectorDetails | None = Field(
        default=None,
        description="Provider-specific data when connected; null otherwise.",
    )


class CallsConnectorDetails(BaseModel):
    """Calls-specific payload when the Calls connector is connected."""

    model_config = ConfigDict(extra="forbid")

    connection_id: uuid.UUID | None = Field(
        default=None,
        description="tenant_connections.id for this Calls link.",
    )
    provider_email: str | None = None
    last_sync_at: datetime | None = Field(
        default=None,
        description="Legacy per-tool ingestion was removed; this value is always null.",
    )


class CallsConnectorStatusItem(BaseModel):
    """Status row for the Calls integration."""

    model_config = ConfigDict(extra="forbid")

    provider: Literal["calls"] = Field(
        default="calls",
        description="Stable id; matches URL segment DELETE /connectors/{provider}.",
    )
    display_name: str = Field(description="Human-readable label for UI.")
    connector_configured: bool = Field(
        description="Server has required credentials/env for this provider.",
    )
    connected: bool = Field(description="Tenant has completed connect for this provider.")
    details: CallsConnectorDetails | None = Field(
        default=None,
        description="Provider-specific data when connected; null otherwise.",
    )


ConnectorStatusItem: TypeAlias = (
    GithubConnectorStatusItem
    | LinearConnectorStatusItem
    | SlackConnectorStatusItem
    | NotionConnectorStatusItem
    | CallsConnectorStatusItem
)


ConnectorInstallPrepareProvider: TypeAlias = Literal["github", "linear", "notion", "slack", "calls"]


class PrepareConnectorInstallBody(BaseModel):
    """POST /connectors/install/prepare — mint short-lived ``install_ticket`` for OAuth navigation."""

    model_config = ConfigDict(extra="forbid")

    provider: ConnectorInstallPrepareProvider


class PrepareConnectorInstallResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    install_ticket: str = Field(description="JWT; pass as ``install_ticket`` query on GET …/install.")
    provider: str


class ConnectorsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[
        Annotated[
            GithubConnectorStatusItem
            | LinearConnectorStatusItem
            | SlackConnectorStatusItem
            | NotionConnectorStatusItem
            | CallsConnectorStatusItem,
            Field(discriminator="provider"),
        ]
    ] = Field(description="One entry per registered runtime provider.")
