"""Tests for onboarding LLM helpers."""

from __future__ import annotations

from unittest.mock import patch

from vector.domains.onboarding.constants import PROFILE_PHASE_NAME, STEP_CHAT_PROFILE
from vector.domains.onboarding.onboarding_llm import (
    BOOTSTRAP_OPENING_REPLY_TEXT,
    extract_onboarding_known_facts,
    generate_onboarding_reply,
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
        assert out == BOOTSTRAP_OPENING_REPLY_TEXT
        m.assert_not_called()

    with patch("vector.domains.onboarding.onboarding_llm.OpenAI") as m:
        out2 = generate_onboarding_reply(
            step=STEP_CHAT_PROFILE,
            answers_json={"profile_phase": PROFILE_PHASE_NAME},
            last_user_message=None,
            assistant_prompt_context={"profile_phase": PROFILE_PHASE_NAME},
            settings=None,
        )
        assert out2 == BOOTSTRAP_OPENING_REPLY_TEXT
        m.assert_not_called()

