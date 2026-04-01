"""Product onboarding API payloads."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OnboardingMessageItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


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
    messages: list[OnboardingMessageItem] = Field(
        default_factory=list,
        description="Persisted onboarding chat turns (chronological), when onboarding_messages table exists.",
    )
    github_connected: bool = Field(
        default=False,
        description=(
            "Derived from tenant_connections / GitHub detail — not stored in onboarding row."
        ),
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


class OnboardingChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str | None = Field(
        default=None, description="User chat text (optional if structured_action is set)."
    )
    structured_action: dict[str, Any] | None = Field(
        default=None,
        description="Deterministic inputs (e.g. tools_selected).",
    )

    @model_validator(mode="after")
    def require_payload(self) -> Self:
        if self.message is None and self.structured_action is None:
            msg = "Either message or structured_action is required."
            raise ValueError(msg)
        return self


class OnboardingChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assistant_message: str
    step: str
    answers: dict[str, Any] = Field(description="Full merged answers_json after this turn.")
