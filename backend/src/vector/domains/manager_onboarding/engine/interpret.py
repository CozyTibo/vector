"""OpenAI JSON calls: interpret (patch only) and reply (assistant_message only)."""

from __future__ import annotations

import json
import logging
from typing import Any

from vector.openai_chat_params import (
    manager_onboarding_completion_cap,
    temperature_for_chat_model,
)

log = logging.getLogger("app")

_MAX_USER_CHARS = 12_000
_MAX_ASSISTANT_CHARS = 4_000


def parse_interpret_response(raw_text: str) -> dict[str, Any] | None:
    """Parse model output into patch dict. Returns None on failure."""
    s = (raw_text or "").strip()
    if not s:
        return None
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        log.info("manager_onboarding interpret: JSON decode failed")
        return None
    if not isinstance(data, dict):
        return None
    patch = data.get("patch")
    if patch is None:
        patch = {}
    if not isinstance(patch, dict):
        return None
    return patch


def parse_reply_response(raw_text: str) -> str | None:
    """Parse model output into assistant_message string. Returns None on failure."""
    s = (raw_text or "").strip()
    if not s:
        return None
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        log.info("manager_onboarding reply: JSON decode failed")
        return None
    if not isinstance(data, dict):
        return None
    msg = data.get("assistant_message")
    if not isinstance(msg, str):
        return None
    msg = msg.strip()[:_MAX_ASSISTANT_CHARS]
    return msg if msg else None


def _chat_json_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    settings: Any,
    max_completion_tokens: int,
    temperature: float,
) -> tuple[str | None, str | None, str | None]:
    """
    Returns (raw_message_content, model_name, error).

    On failure returns (None, model_or_none, error_message).
    """
    key = (getattr(settings, "openai_api_key", None) or "").strip()
    if not key:
        return None, None, "missing_openai_api_key"
    user = (user_prompt or "").strip()[:_MAX_USER_CHARS]
    if not user:
        return None, None, "empty_user_prompt"
    model = getattr(settings, "openai_model", "gpt-4o-mini")
    try:
        from openai import OpenAI
    except ImportError:
        return None, None, "openai_import_error"
    try:
        client = OpenAI(api_key=key)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user},
            ],
            # Newer models (e.g. gpt-5.1) reject ``max_tokens`` on this endpoint.
            "max_completion_tokens": max_completion_tokens,
            "response_format": {"type": "json_object"},
        }
        temp = temperature_for_chat_model(model, temperature)
        if temp is not None:
            kwargs["temperature"] = temp
        resp = client.chat.completions.create(**kwargs)
        choice = resp.choices[0].message.content
        return (choice or "").strip(), model, None
    except Exception as e:
        log.info("manager_onboarding LLM call failed: %s", e)
        return None, model, str(e)


def run_onboarding_interpret(
    *,
    system_prompt: str,
    user_prompt: str,
    settings: Any,
) -> tuple[dict[str, Any], str | None, str | None]:
    """
    Interpret step: extract ``patch`` only.

    Returns (patch_dict, model_name, error). On failure: ({}, None|model, error).
    """
    cap = manager_onboarding_completion_cap(
        (getattr(settings, "openai_model", None) or "gpt-4o-mini").strip(),
        interpret=True,
    )
    raw, model, err = _chat_json_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        settings=settings,
        max_completion_tokens=cap,
        temperature=0.35,
    )
    if err:
        return {}, model, err
    parsed = parse_interpret_response((raw or "").strip())
    if parsed is None:
        return {}, model, "json_parse_failed"
    return parsed, model, None


def run_onboarding_reply(
    *,
    system_prompt: str,
    user_prompt: str,
    settings: Any,
) -> tuple[str, str | None, str | None]:
    """
    Reply step: produce ``assistant_message`` only (post-merge context).

    Returns (assistant_message, model_name, error). On failure: ("", model, error).
    """
    cap = manager_onboarding_completion_cap(
        (getattr(settings, "openai_model", None) or "gpt-4o-mini").strip(),
        interpret=False,
    )
    raw, model, err = _chat_json_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        settings=settings,
        max_completion_tokens=cap,
        temperature=0.35,
    )
    if err:
        return "", model, err
    parsed = parse_reply_response((raw or "").strip())
    if parsed is None:
        return "", model, "json_parse_failed"
    return parsed, model, None
