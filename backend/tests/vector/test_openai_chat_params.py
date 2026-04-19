from vector.openai_chat_params import (
    manager_onboarding_completion_cap,
    onboarding_chat_max_completion_tokens,
    temperature_for_chat_model,
)


def test_gpt5_uses_provider_default_temperature() -> None:
    assert temperature_for_chat_model("gpt-5-mini", 0.35) is None
    assert temperature_for_chat_model("gpt-5.1-2025-11-13", 0.2) is None


def test_gpt4o_passes_requested_temperature() -> None:
    assert temperature_for_chat_model("gpt-4o-mini", 0.35) == 0.35


def test_gpt5_higher_completion_cap() -> None:
    assert manager_onboarding_completion_cap("gpt-5-mini", interpret=True) == 4096
    assert manager_onboarding_completion_cap("gpt-5-mini", interpret=False) == 3072
    assert manager_onboarding_completion_cap("gpt-4o-mini", interpret=True) == 900


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
