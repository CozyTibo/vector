"""API response models for current session."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    user_id: uuid.UUID
    email: str
    full_name: str | None
    tenant_id: uuid.UUID
    company_name: str
    tenant_slug: str
    role: str = Field(description="Membership role in current tenant")
    onboarding_completed: bool = Field(
        default=False,
        description="True when onboarding_state exists and status is completed.",
    )
    connected_connectors: list[str] = Field(
        default_factory=list,
        description="Active tenant_connections.provider values for this workspace.",
    )
