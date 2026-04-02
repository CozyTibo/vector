"""Unit tests for deterministic onboarding_flow.handle_turn."""

from __future__ import annotations

from vector.domains.onboarding.constants import (
    PROFILE_PHASE_CONNECTORS_INTRO,
    PROFILE_PHASE_DONE,
    PROFILE_PHASE_ORG,
    PROFILE_PHASE_ROLE,
    PROFILE_PHASE_SIZE,
    PROFILE_PHASE_TOOLS,
    PROFILE_PHASE_WEBSITE,
    STEP_CHAT_PROFILE,
    STEP_CONNECT_COMMUNICATION,
    STEP_CONNECT_GITHUB,
    STEP_CONNECT_LINEAR,
    STEP_SCANNING,
)
from vector.domains.onboarding.onboarding_flow import handle_turn


def _base_answers() -> dict:
    return {"profile_phase": "name"}


def test_company_size_numeric_86_maps_to_50_plus() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_SIZE,
        "profile": {"name": "Tibo", "role": "Founder"},
        "company": {"name": "LaboiteKiTue"},
    }
    r = handle_turn(STEP_CHAT_PROFILE, "86", None, a)
    assert r.answers_updates["company"]["size"] == "50+"
    assert r.answers_updates["profile_phase"] == PROFILE_PHASE_CONNECTORS_INTRO


def test_role_typo_foundr_normalized_to_founder() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_ROLE,
        "profile": {"name": "Tibo"},
        "company": {"name": "Acme"},
    }
    r = handle_turn(STEP_CHAT_PROFILE, "Foundr", None, a)
    assert r.answers_updates["profile"]["role"] == "Founder"
    assert r.answers_updates["profile_phase"] == PROFILE_PHASE_SIZE


def test_legacy_profile_phase_website_skips_to_company_size() -> None:
    """Stored answers from before website step removal advance to headcount."""
    a = {
        "profile_phase": PROFILE_PHASE_WEBSITE,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme"},
    }
    r = handle_turn(STEP_CHAT_PROFILE, "12", None, a)
    assert r.answers_updates["company"]["size"] == "5-15"
    assert r.answers_updates["profile_phase"] == PROFILE_PHASE_CONNECTORS_INTRO


def test_profile_sequence_name_through_size() -> None:
    a = _base_answers()
    r1 = handle_turn(STEP_CHAT_PROFILE, "Ada", None, a)
    assert r1.next_step == STEP_CHAT_PROFILE
    assert r1.answers_updates["profile"]["name"] == "Ada"
    assert r1.answers_updates["profile_phase"] == PROFILE_PHASE_ORG
    instr = r1.assistant_prompt_context["instruction"]
    assert "Ada" in instr
    assert "warm" in instr.lower()

    a = {**a, **r1.answers_updates}
    r2 = handle_turn(STEP_CHAT_PROFILE, "Acme", None, a)
    assert r2.answers_updates["company"]["name"] == "Acme"
    assert r2.answers_updates["profile_phase"] == PROFILE_PHASE_ROLE

    a = {**a, **r2.answers_updates}
    r3 = handle_turn(STEP_CHAT_PROFILE, "Founder", None, a)
    assert r3.answers_updates["profile"]["role"] == "Founder"
    assert r3.answers_updates["profile_phase"] == PROFILE_PHASE_SIZE

    a = {**a, **r3.answers_updates}
    r4 = handle_turn(STEP_CHAT_PROFILE, "5-15", None, a)
    assert r4.answers_updates["company"]["size"] == "5-15"
    assert r4.answers_updates["profile_phase"] == PROFILE_PHASE_CONNECTORS_INTRO


def test_connectors_intro_question_does_not_advance_phase() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_CONNECTORS_INTRO,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    r = handle_turn(STEP_CHAT_PROFILE, "Do you store our Slack messages?", None, a)
    assert r.answers_updates == {}
    assert r.assistant_prompt_context.get("connectors_privacy_kb")


def test_connectors_intro_ready_advances_to_tools() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_CONNECTORS_INTRO,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, {"type": "connectors_intro_ready"}, a)
    assert r.answers_updates["profile_phase"] == PROFILE_PHASE_TOOLS


def test_tools_selected_github_only_goes_connect_github() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_TOOLS,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    action = {
        "type": "tools_selected",
        "tools": {
            "engineering": ["github"],
            "pm": [],
            "communication": [],
            "docs": [],
        },
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a)
    assert r.next_step == STEP_CONNECT_GITHUB
    assert r.answers_updates["profile_phase"] == PROFILE_PHASE_DONE
    assert "github" in r.answers_updates["tools"]["engineering"]


def test_tools_selected_teams_only_goes_connect_comm() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_TOOLS,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    action = {
        "type": "tools_selected",
        "tools": {
            "engineering": [],
            "pm": [],
            "communication": ["ms_teams"],
            "docs": [],
        },
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a)
    assert r.next_step == STEP_CONNECT_COMMUNICATION


def test_tools_selected_moves_to_connect_slack_with_tools_merged() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_TOOLS,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    action = {
        "type": "tools_selected",
        "tools": {
            "engineering": ["github"],
            "pm": ["linear"],
            "communication": ["slack"],
            "docs": ["notion"],
        },
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a)
    assert r.next_step == STEP_CONNECT_COMMUNICATION
    assert r.answers_updates["profile_phase"] == PROFILE_PHASE_DONE
    assert "github" in r.answers_updates["tools"]["engineering"]
    assert "linear" in r.answers_updates["tools"]["pm"]
    assert r.answers_updates["connect_queue"] == ["slack", "linear", "github"]


def test_tools_selected_skips_already_connected_slack() -> None:
    """Re-confirming tools after Slack OAuth should not send user back to Connect Slack."""
    a = {
        "profile_phase": PROFILE_PHASE_TOOLS,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    action = {
        "type": "tools_selected",
        "tools": {
            "engineering": ["github"],
            "pm": ["linear"],
            "communication": ["slack"],
            "docs": ["notion"],
        },
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a, slack_connected=True)
    assert r.next_step == STEP_CONNECT_LINEAR
    assert r.answers_updates["connect_queue"] == ["linear", "github"]


def test_tools_selected_all_live_connectors_linked_goes_scanning() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_TOOLS,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    action = {
        "type": "tools_selected",
        "tools": {
            "engineering": ["github"],
            "pm": ["linear"],
            "communication": ["slack"],
            "docs": [],
        },
    }
    r = handle_turn(
        STEP_CHAT_PROFILE,
        None,
        action,
        a,
        slack_connected=True,
        linear_connected=True,
        github_connected=True,
    )
    assert r.next_step == STEP_SCANNING
    assert r.answers_updates["connect_queue"] == []


def test_connect_slack_message_advances_to_github_when_github_selected() -> None:
    a = {
        "tools": {
            "engineering": ["github"],
            "pm": [],
            "communication": [],
            "docs": [],
        }
    }
    r = handle_turn(STEP_CONNECT_COMMUNICATION, "ok", None, a)
    assert r.next_step == STEP_CONNECT_GITHUB
    assert r.answers_updates["connect_queue"] == ["github"]


def test_connect_slack_no_live_tools_goes_scanning() -> None:
    a = {"tools": {"engineering": [], "pm": [], "communication": ["slack"], "docs": []}}
    r = handle_turn(STEP_CONNECT_COMMUNICATION, "continue", None, a)
    assert r.next_step == STEP_SCANNING


def test_connect_slack_linear_only() -> None:
    a = {"tools": {"engineering": [], "pm": ["linear"], "communication": [], "docs": []}}
    r = handle_turn(STEP_CONNECT_COMMUNICATION, "go", None, a)
    assert r.next_step == STEP_CONNECT_LINEAR
    assert r.answers_updates["connect_queue"] == ["linear"]
