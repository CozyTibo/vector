from vector.openai_chat_params import (
    max_completion_tokens_for_manager_insights_insights,
    max_completion_tokens_for_manager_insights_interpretations,
    max_completion_tokens_for_manager_insights_perception,
    onboarding_chat_max_completion_tokens,
    temperature_for_chat_model,
)


def test_gpt5_uses_provider_default_temperature() -> None:
    assert temperature_for_chat_model("gpt-5-mini", 0.35) is None
    assert temperature_for_chat_model("gpt-5.1-2025-11-13", 0.2) is None


def test_gpt4o_passes_requested_temperature() -> None:
    assert temperature_for_chat_model("gpt-4o-mini", 0.35) == 0.35


def test_onboarding_chat_gpt5_uses_high_completion_cap() -> None:
    assert (
        onboarding_chat_max_completion_tokens(
            "gpt-5-mini",
            intro_kind=None,
            has_connectors_privacy_kb=False,
        )
        == 4096
    )


def test_onboarding_chat_gpt4o_keeps_tight_caps() -> None:
    assert (
        onboarding_chat_max_completion_tokens(
            "gpt-4o-mini",
            intro_kind=None,
            has_connectors_privacy_kb=False,
        )
        == 220
    )
    assert (
        onboarding_chat_max_completion_tokens(
            "gpt-4o-mini",
            intro_kind="after_size",
            has_connectors_privacy_kb=False,
        )
        == 200
    )


def test_manager_insights_gpt5_uses_high_completion_cap() -> None:
    assert max_completion_tokens_for_manager_insights_interpretations("gpt-5-mini") == 16_384


def test_manager_insights_o_series_uses_high_completion_cap() -> None:
    assert max_completion_tokens_for_manager_insights_interpretations("o3-mini") == 16_384


def test_manager_insights_gpt4o_uses_default_cap() -> None:
    assert max_completion_tokens_for_manager_insights_interpretations("gpt-4o-mini") == 4096


def test_manager_insights_step8_gpt5_uses_high_completion_cap() -> None:
    assert max_completion_tokens_for_manager_insights_insights("gpt-5-mini") == 16_384


def test_manager_insights_step8_gpt4o_uses_default_cap() -> None:
    assert max_completion_tokens_for_manager_insights_insights("gpt-4o-mini") == 4096


def test_manager_insights_perception_matches_interpretations_caps() -> None:
    assert max_completion_tokens_for_manager_insights_perception("gpt-5-mini") == 16_384
    assert max_completion_tokens_for_manager_insights_perception("gpt-4o-mini") == 4096
