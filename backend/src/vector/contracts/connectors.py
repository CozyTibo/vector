"""API payloads for tenant connectors (multi-provider)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal, TypeAlias

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
        description="Max fetched_at over raw_ingestion_records for this connection, if any.",
    )


class GithubIngestionSyncResponse(BaseModel):
    """Result of POST /connectors/github/sync (HTTP 202: run queued; poll ingestion runs)."""

    model_config = ConfigDict(extra="forbid")

    run_id: uuid.UUID
    status: str
    error_summary: str | None = None
    stats: dict[str, Any] | None = None


class GithubIngestionRunListItem(BaseModel):
    """One persisted ingestion run for this tenant (GitHub poll/webhook/…)."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    connection_id: uuid.UUID
    status: str
    source_trigger: str
    started_at: datetime
    finished_at: datetime | None
    error_summary: str | None
    stats: dict[str, Any] | None
    records_written: int = Field(description="Rows in raw_ingestion_records for this run.")


class GithubIngestionRunsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[GithubIngestionRunListItem]


class GithubRawIngestionRecordItem(BaseModel):
    """One append-only raw envelope (resource-level)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    replay_sequence: int
    resource_type: str
    external_id: str
    api_endpoint: str
    query_params: dict[str, Any]
    payload_hash: str
    http_status: int
    fetched_at: datetime
    payload_body: dict[str, Any]


class GithubIngestionRecordsPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: uuid.UUID
    total: int
    limit: int
    offset: int
    items: list[GithubRawIngestionRecordItem]


class LinearIngestionSyncResponse(BaseModel):
    """Result of POST /connectors/linear/sync — run is queued (HTTP 202); Step 1 runs on the worker."""

    model_config = ConfigDict(extra="forbid")

    run_id: uuid.UUID
    status: str
    error_summary: str | None = None
    stats: dict[str, Any] | None = None


class LinearIngestionRunListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    connection_id: uuid.UUID
    status: str
    source_trigger: str
    started_at: datetime
    finished_at: datetime | None
    error_summary: str | None
    stats: dict[str, Any] | None
    records_written: int = Field(description="Rows in raw_ingestion_records for this run.")


class LinearIngestionRunsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[LinearIngestionRunListItem]


class LinearRawIngestionRecordItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    replay_sequence: int
    resource_type: str
    external_id: str
    api_endpoint: str
    query_params: dict[str, Any]
    payload_hash: str
    http_status: int
    fetched_at: datetime
    payload_body: dict[str, Any]


class LinearIngestionRecordsPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: uuid.UUID
    total: int
    limit: int
    offset: int
    items: list[LinearRawIngestionRecordItem]


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
        description="Max fetched_at over raw_ingestion_records for this connection, if any.",
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
        description="Max fetched_at over raw_ingestion_records for this connection, if any.",
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


ConnectorStatusItem: TypeAlias = (
    GithubConnectorStatusItem | LinearConnectorStatusItem | SlackConnectorStatusItem
)


class ConnectorsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[
        Annotated[
            GithubConnectorStatusItem | LinearConnectorStatusItem | SlackConnectorStatusItem,
            Field(discriminator="provider"),
        ]
    ] = Field(description="One entry per registered runtime provider.")
