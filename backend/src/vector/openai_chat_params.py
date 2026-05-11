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


def onboarding_chat_max_completion_tokens(
    model: str,
    *,
    intro_kind: str | None,
    has_connectors_privacy_kb: bool,
) -> int:
    """
    ``max_completion_tokens`` for website onboarding chat (profile + connectors intro).

    ``gpt-5*`` reasoning models spend much of the completion budget on hidden reasoning; caps
    like 220 often yield **empty** ``message.content`` with HTTP 200, which would otherwise
    surface raw internal ``instruction`` text as a fallback (bad UX).
    """
    m = (model or "").strip().lower()
    if m.startswith("gpt-5"):
        return 4096
    if intro_kind in ("after_size", "after_role"):
        return 200
    if intro_kind == "qa" and has_connectors_privacy_kb:
        return 320
    if has_connectors_privacy_kb:
        return 280
    return 220


