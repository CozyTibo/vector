"""Typed outbound email payload (serializable for Celery JSON)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmailEnvelope(BaseModel):
    """One logical message: recipients, subject, plain text, optional HTML."""

    model_config = ConfigDict(str_strip_whitespace=True)

    to: list[EmailStr] = Field(min_length=1, description="Recipients (To).")
    subject: str = Field(min_length=1, max_length=998)
    body_text: str = Field(min_length=1)
    body_html: str | None = None
    reply_to: EmailStr | None = None

    def to_task_payload(self) -> dict[str, Any]:
        """JSON-safe dict for Celery ``json`` serializer."""
        return self.model_dump(mode="json")

    @classmethod
    def from_task_payload(cls, data: dict[str, Any]) -> EmailEnvelope:
        return cls.model_validate(data)
