"""Deterministic stub LLM — CI / golden tests only (**FakeLlmAdapter**)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.synthesis.adapters.llm.protocol import (
    LlmAdapterError,
    LlmCompletionRequestV1,
    LlmCompletionResultV1,
    LLM_RESPONSE_FORMAT_JSON_SCHEMA_V1,
)

FAKE_LLM_ADAPTER_ID_V1: Final[str] = "FakeLlmAdapter"
FAKE_LLM_STRUCT_COMPLETION_FIXTURE_V1: Final[str] = "FakeLlmStructCompletionV1_Default.json"

_REQUIRED_COMPLETION_KEYS_V1: Final[frozenset[str]] = frozenset({"schema_version", "discourse_phrases"})


def _repo_root_v1() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        if (root / "DOCS" / "cortex" / "synthesis" / "fixtures").is_dir():
            return root
    return start.parents[7]


def load_fake_llm_struct_completion_fixture_v1() -> dict[str, Any]:
    path = _repo_root_v1() / "DOCS" / "cortex" / "synthesis" / "fixtures" / FAKE_LLM_STRUCT_COMPLETION_FIXTURE_V1
    if not path.is_file():
        raise LlmAdapterError("fake_llm_fixture_not_found", detail={"path": str(path)})
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise LlmAdapterError("invalid_fake_llm_fixture")
    return raw


def validate_structured_completion_v1(completion: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = _REQUIRED_COMPLETION_KEYS_V1 - set(completion.keys())
    if missing:
        errors.append(f"missing_keys:{sorted(missing)}")
    phrases = completion.get("discourse_phrases")
    if phrases is not None and not isinstance(phrases, list):
        errors.append("discourse_phrases_not_list")
    elif isinstance(phrases, list):
        for idx, row in enumerate(phrases):
            if not isinstance(row, dict):
                errors.append(f"discourse_phrase_not_object:{idx}")
                continue
            if not row.get("claim_id"):
                errors.append(f"discourse_phrase_missing_claim_id:{idx}")
    return errors


def build_default_discourse_phrases_v1(context: Mapping[str, Any]) -> list[dict[str, str]]:
    """Deterministic discourse fill from claim slots when fixture phrases are empty."""
    slots = context.get("claim_slots")
    if not isinstance(slots, list):
        return []
    out: list[dict[str, str]] = []
    for row in slots:
        if not isinstance(row, dict):
            continue
        if not row.get("discourse_only"):
            continue
        claim_id = str(row.get("claim_id") or "")
        if not claim_id:
            continue
        out.append(
            {
                "claim_id": claim_id,
                "phrase": f"discourse:{claim_id}",
            },
        )
    return out


class FakeLlmAdapter:
    """Returns fixture JSON — never calls a live vendor API."""

    def complete_structured_v1(self, request: LlmCompletionRequestV1) -> LlmCompletionResultV1:
        if request.response_format != LLM_RESPONSE_FORMAT_JSON_SCHEMA_V1:
            raise LlmAdapterError(
                "unsupported_response_format",
                detail={"response_format": request.response_format},
            )
        simulate = (request.simulate or "").strip().lower()
        if simulate == "timeout":
            raise LlmAdapterError("llm_timeout")
        if simulate == "policy":
            raise LlmAdapterError("llm_policy_refusal")
        completion: dict[str, Any]
        if simulate == "schema":
            completion = {"schema_version": 1}
        else:
            completion = dict(load_fake_llm_struct_completion_fixture_v1())
            if not completion.get("discourse_phrases"):
                completion["discourse_phrases"] = build_default_discourse_phrases_v1(request.context)
        errors = validate_structured_completion_v1(completion)
        if errors or simulate == "schema":
            raise LlmAdapterError("llm_schema_invalid", detail={"violations": errors or ["simulated_schema"]})
        tokens_used = max(1, len(json.dumps(completion, sort_keys=True)) // 4)
        return LlmCompletionResultV1(
            completion=completion,
            completion_hash=hash_reasoning_canonical_json_sha256_v1(completion),
            tokens_used=tokens_used,
            provider_request_id=f"fake-{request.model_route_id}",
            raw_status="ok",
        )
