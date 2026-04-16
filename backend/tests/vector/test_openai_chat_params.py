from vector.openai_chat_params import (
    manager_onboarding_completion_cap,
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
