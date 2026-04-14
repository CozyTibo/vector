"""Chat Completions parameter quirks by model id (aliases and dated snapshots)."""

from __future__ import annotations


def temperature_for_chat_model(model: str, requested: float) -> float | None:
    """
    Return a temperature to send to the API, or ``None`` to omit the field (provider default).

    ``gpt-5*`` models reject non-default ``temperature`` on Chat Completions.
    """
    m = (model or "").strip().lower()
    if m.startswith("gpt-5"):
        return None
    return requested


def manager_onboarding_completion_cap(model: str, *, interpret: bool) -> int:
    """
    ``max_completion_tokens`` for manager-onboarding JSON calls.

    ``gpt-5*`` models spend completion budget on hidden reasoning tokens; too low a cap
    yields empty content and parse failures.
    """
    m = (model or "").strip().lower()
    if m.startswith("gpt-5"):
        # Reply step benefits from a higher cap (reasoning models burn hidden tokens).
        return 4096 if interpret else 3072
    return 900 if interpret else 900
