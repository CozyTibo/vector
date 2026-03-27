"""Product onboarding API payloads."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class OnboardingGetResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    status: str
    current_step: str
    answers: dict[str, Any] = Field(description="Mirrors answers_json")
    version: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    abandoned_at: datetime | None = None
    github_connected: bool = Field(
        default=False,
        description="Derived from tenant_connections / GitHub detail — not stored in onboarding row.",
    )
    linear_connected: bool = Field(
        default=False,
        description="Derived from Linear OAuth connection for tenant.",
    )


class OnboardingPatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_step: str | None = None
    answers: dict[str, Any] | None = None


class OnboardingCompleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    current_step: str
    completed_at: datetime
