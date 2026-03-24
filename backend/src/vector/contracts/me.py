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
