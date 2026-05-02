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
    if intro_kind == "after_size":
        return 200
    if intro_kind == "qa" and has_connectors_privacy_kb:
        return 320
    if has_connectors_privacy_kb:
        return 280
    return 220


def _manager_insights_reasoning_style_model(model: str) -> bool:
    """Models that may allocate completion budget to hidden reasoning before visible JSON."""
    m = (model or "").strip().lower()
    if m.startswith("gpt-5"):
        return True
    # OpenAI o-series (and similar ids) — same empty-content + finish_reason=length failure mode.
    return m.startswith(("o1", "o3", "o4"))


def max_completion_tokens_for_manager_insights_interpretations(model: str) -> int:
    """
    Step 7 (manager insights) uses Chat Completions JSON.

    Small caps (e.g. 1400) can yield **empty** ``message.content`` with ``finish_reason="length"``
    when reasoning-style models burn the whole budget internally, or when the model emits a
    long grounded JSON payload. Use a high floor for all models; extra headroom for o / gpt-5.
    """
    if _manager_insights_reasoning_style_model(model):
        return 16_384
    return 4096


def max_completion_tokens_for_manager_insights_insights(model: str) -> int:
    """
    Step 8 (manager insights) uses Chat Completions JSON.

    Same rationale as Step 7: avoid truncation and empty assistant text on long structured output.
    """
    if _manager_insights_reasoning_style_model(model):
        return 16_384
    return 4096


def max_completion_tokens_for_manager_insights_perception(model: str) -> int:
    """§6 coordination — execution-state perception LLM returns grounded JSON rows."""
    if _manager_insights_reasoning_style_model(model):
        return 16_384
    return 4096


def max_completion_tokens_for_manager_insights_decision_interpretation(model: str) -> int:
    """
    Small visible output (three strings), but ``gpt-5*`` / o-style models may allocate much of the
    completion budget to hidden reasoning first — low caps risk empty ``message.content`` (same
    failure mode as ``onboarding_chat_max_completion_tokens``). Use **5120** (4096 + 25% headroom)
    for those models; keep a tight cap for non-reasoning chat models.
    """
    if _manager_insights_reasoning_style_model(model):
        return 5120
    return 512
