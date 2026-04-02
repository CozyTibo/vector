"""Tests for onboarding LLM helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from vector.domains.onboarding.constants import (
    PROFILE_PHASE_CONNECTORS_INTRO,
    PROFILE_PHASE_NAME,
    STEP_CHAT_PROFILE,
)
import vector.domains.onboarding.onboarding_llm as onboarding_llm_mod
from vector.domains.onboarding.onboarding_llm import (
    BOOTSTRAP_OPENING_REPLY_TEXT,
    extract_onboarding_known_facts,
    generate_onboarding_reply,
    split_connectors_intro_after_size,
)


def test_extract_onboarding_known_facts_full() -> None:
    answers = {
        "profile": {"name": "Alex", "role": "Founder"},
        "company": {"name": "Acme", "website": "acme.com", "size": "5-15"},
    }
    f = extract_onboarding_known_facts(answers)
    assert f["user_name"] == "Alex"
    assert f["role"] == "Founder"
    assert f["company_name"] == "Acme"
    assert f["website"] == "acme.com"
    assert f["company_size"] == "5-15"


def test_extract_onboarding_known_facts_empty() -> None:
    f = extract_onboarding_known_facts({})
    assert all(f[k] is None for k in f)


def test_bootstrap_opening_skips_openai_and_handles_missing_profile_phase() -> None:
    """Empty first POST must not call OpenAI (new tenants often have no profile_phase key yet)."""
    with patch("vector.domains.onboarding.onboarding_llm.OpenAI") as m:
        out = generate_onboarding_reply(
            step=STEP_CHAT_PROFILE,
            answers_json={},
            last_user_message=None,
            assistant_prompt_context={},
            settings=None,
        )
        assert out == [BOOTSTRAP_OPENING_REPLY_TEXT]
        m.assert_not_called()

    with patch("vector.domains.onboarding.onboarding_llm.OpenAI") as m:
        out2 = generate_onboarding_reply(
            step=STEP_CHAT_PROFILE,
            answers_json={"profile_phase": PROFILE_PHASE_NAME},
            last_user_message=None,
            assistant_prompt_context={"profile_phase": PROFILE_PHASE_NAME},
            settings=None,
        )
        assert out2 == [BOOTSTRAP_OPENING_REPLY_TEXT]
        m.assert_not_called()


def test_strip_em_dash_from_assistant_copy() -> None:
    assert onboarding_llm_mod._strip_em_dash("a\u2014b") == "a - b"
    assert onboarding_llm_mod._strip_em_dash("a\u2013b") == "a - b"


def test_split_connectors_intro_after_size() -> None:
    parts = split_connectors_intro_after_size("Nice.\n\nSecond part here.\n\nMore.")
    assert parts == ["Nice.", "Second part here.\n\nMore."]


def test_connectors_intro_after_size_fallback_is_two_bubbles_without_openai() -> None:
    ctx = {
        "profile_phase": PROFILE_PHASE_CONNECTORS_INTRO,
        "connectors_intro_kind": "after_size",
    }
    no_ai = MagicMock()
    no_ai.openai_api_key = ""
    no_ai.openai_model = "gpt-4o-mini"
    out = generate_onboarding_reply(
        step=STEP_CHAT_PROFILE,
        answers_json={"profile_phase": PROFILE_PHASE_CONNECTORS_INTRO},
        last_user_message="42",
        assistant_prompt_context=ctx,
        settings=no_ai,
    )
    assert len(out) == 2
    assert "solid team size" in out[0].lower()
    assert "signal" in out[1].lower()
    assert "okay" in out[1].lower() or "quick" in out[1].lower()

