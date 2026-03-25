"""API payloads for tenant connectors (multi-provider)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class GithubConnectorDetails(BaseModel):
    """GitHub-specific payload when the GitHub connector is connected."""

    model_config = ConfigDict(extra="forbid")

    installation_id: int | None = None
    account_login: str | None = None
    account_type: str | None = None


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

    organization_id: str | None = None
    organization_name: str | None = None


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


type ConnectorStatusItem = GithubConnectorStatusItem | LinearConnectorStatusItem


class ConnectorsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[
        Annotated[
            GithubConnectorStatusItem | LinearConnectorStatusItem,
            Field(discriminator="provider"),
        ]
    ] = Field(description="One entry per registered runtime provider.")
