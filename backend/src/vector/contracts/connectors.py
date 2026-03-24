"""API payloads for tenant connectors (multi-provider)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GithubConnectorDetails(BaseModel):
    """GitHub-specific payload when the GitHub connector is connected."""

    model_config = ConfigDict(extra="forbid")

    installation_id: int | None = None
    account_login: str | None = None
    account_type: str | None = None


class GithubConnectorStatusItem(BaseModel):
    """Status row for the GitHub integration (discriminated by `provider`).

    When adding providers, introduce `SlackConnectorStatusItem`, etc., then set
    ``ConnectorStatusItem`` to a discriminated union with ``Field(discriminator='provider')``.
    """

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


# Union root: extend with `SlackConnectorStatusItem | ...` and a Pydantic discriminator when needed.
type ConnectorStatusItem = GithubConnectorStatusItem


class ConnectorsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ConnectorStatusItem] = Field(
        description="One entry per registered runtime provider.",
    )
