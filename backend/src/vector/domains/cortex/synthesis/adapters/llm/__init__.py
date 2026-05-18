"""Phase 08 P08-11 — LLM vendor isolation (**SYN-AI-01**)."""

from vector.domains.cortex.synthesis.adapters.llm.fake_llm_adapter import FakeLlmAdapter
from vector.domains.cortex.synthesis.adapters.llm.protocol import (
    LlmAdapterError,
    LlmCompletionRequestV1,
    LlmCompletionResultV1,
)

__all__ = [
    "FakeLlmAdapter",
    "LlmAdapterError",
    "LlmCompletionRequestV1",
    "LlmCompletionResultV1",
]
