"""LLM adapter protocol — Phase **08** Step **11** (no vendor SDKs here)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final, Protocol


class LlmAdapterError(ValueError):
    """Adapter-level completion failure (mapped to SD-LLM-* by router)."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


LLM_RESPONSE_FORMAT_JSON_SCHEMA_V1: Final[str] = "json_schema"


@dataclass(frozen=True, slots=True)
class LlmCompletionRequestV1:
    model_route_id: str
    provider: str
    model: str
    temperature: float
    max_tokens: int
    response_format: str
    prompt_hash: str
    context: dict[str, Any]
    simulate: str | None = None


@dataclass(frozen=True, slots=True)
class LlmCompletionResultV1:
    completion: dict[str, Any]
    completion_hash: str
    tokens_used: int
    provider_request_id: str = ""
    raw_status: str = "ok"


class LlmAdapterProtocol(Protocol):
    def complete_structured_v1(self, request: LlmCompletionRequestV1) -> LlmCompletionResultV1: ...
