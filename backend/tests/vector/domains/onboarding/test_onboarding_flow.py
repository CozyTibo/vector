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
    STEP_ADMIN_ACCESS,
    STEP_CHAT_PROFILE,
    STEP_CONNECT_COMMUNICATION,
    STEP_CONNECT_PROJECT_MANAGEMENT,
    STEP_SLACK_STAKEHOLDERS,
    STEP_SCANNING,
    STEP_UNSUPPORTED_MANDATORY_TOOLS,
)
from vector.domains.onboarding.onboarding_flow import handle_turn


def _base_answers() -> dict:
    return {"profile_phase": "name"}


def test_company_size_numeric_86_stores_exact_string() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_SIZE,
        "profile": {"name": "Tibo", "role": "Founder"},
        "company": {"name": "LaboiteKiTue"},
    }
    r = handle_turn(STEP_CHAT_PROFILE, "86", None, a)
    assert r.answers_updates["company"]["size"] == "86"
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


def test_role_pure_number_does_not_advance_or_store() -> None:
    """Numeric replies on the role step are headcount confusion; stay on role."""
    a = {
        "profile_phase": PROFILE_PHASE_ROLE,
        "profile": {"name": "Tobias"},
        "company": {"name": "Lakaka"},
    }
    r = handle_turn(STEP_CHAT_PROFILE, "345", None, a)
    assert r.answers_updates == {}
    assert r.assistant_prompt_context["profile_phase"] == PROFILE_PHASE_ROLE
    assert "role" in r.assistant_prompt_context["instruction"].lower()


def test_legacy_profile_phase_website_skips_to_company_size() -> None:
    """Stored answers from before website step removal advance to headcount."""
    a = {
        "profile_phase": PROFILE_PHASE_WEBSITE,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme"},
    }
    r = handle_turn(STEP_CHAT_PROFILE, "12", None, a)
    assert r.answers_updates["company"]["size"] == "12"
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
    assert r.assistant_prompt_context.get("connectors_intro_kind") == "qa"


def test_connectors_intro_ready_advances_to_tools() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_CONNECTORS_INTRO,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, {"type": "connectors_intro_ready"}, a)
    assert r.answers_updates["profile_phase"] == PROFILE_PHASE_TOOLS


def test_tools_selected_without_communication_does_not_advance() -> None:
    """At least one communication tool is required before confirming."""
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
    assert r.next_step == STEP_CHAT_PROFILE
    assert r.answers_updates == {}
    assert r.assistant_prompt_context["profile_phase"] == PROFILE_PHASE_TOOLS


def test_tools_selected_without_pm_does_not_advance() -> None:
    """At least one PM tool is required (with communication and engineering)."""
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
            "communication": ["slack"],
            "docs": [],
        },
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a)
    assert r.next_step == STEP_CHAT_PROFILE
    assert r.answers_updates == {}
    assert "project management" in r.assistant_prompt_context["instruction"].lower()


def test_tools_selected_without_engineering_does_not_advance() -> None:
    """At least one engineering tool is required (with communication and PM)."""
    a = {
        "profile_phase": PROFILE_PHASE_TOOLS,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    action = {
        "type": "tools_selected",
        "tools": {
            "engineering": [],
            "pm": ["linear"],
            "communication": ["slack"],
            "docs": [],
        },
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a)
    assert r.next_step == STEP_CHAT_PROFILE
    assert r.answers_updates == {}
    assert "engineering" in r.assistant_prompt_context["instruction"].lower()


def test_tools_selected_slack_linear_github_queues_pm_then_eng_then_slack() -> None:
    """Linear, GitHub, then Slack are queued for in-product OAuth."""
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
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a)
    assert r.next_step == STEP_CONNECT_PROJECT_MANAGEMENT
    assert r.answers_updates["profile_phase"] == PROFILE_PHASE_DONE
    assert "github" in r.answers_updates["tools"]["engineering"]
    assert r.answers_updates["connect_queue"] == ["linear", "github", "slack"]
    assert r.answers_updates.get("unsupported_mandatory_sections") == []


def test_tools_selected_teams_only_goes_unsupported_mandatory() -> None:
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
            "communication": ["ms_teams"],
            "docs": [],
        },
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a)
    assert r.next_step == STEP_UNSUPPORTED_MANDATORY_TOOLS
    assert r.answers_updates["unsupported_mandatory_sections"] == ["communication"]
    assert r.answers_updates["connect_queue"] == []


def test_tools_selected_slack_jira_github_goes_unsupported_mandatory_with_slack_queued() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_TOOLS,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    action = {
        "type": "tools_selected",
        "tools": {
            "engineering": ["github"],
            "pm": ["jira"],
            "communication": ["slack"],
            "docs": [],
        },
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a)
    assert r.next_step == STEP_UNSUPPORTED_MANDATORY_TOOLS
    assert r.answers_updates["unsupported_mandatory_sections"] == ["pm"]
    assert r.answers_updates["connect_queue"] == ["slack"]


def test_tools_selected_slack_linear_gitlab_goes_unsupported_mandatory_eng_only() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_TOOLS,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    action = {
        "type": "tools_selected",
        "tools": {
            "engineering": ["gitlab"],
            "pm": ["linear"],
            "communication": ["slack"],
            "docs": [],
        },
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a)
    assert r.next_step == STEP_UNSUPPORTED_MANDATORY_TOOLS
    assert r.answers_updates["unsupported_mandatory_sections"] == ["engineering"]
    assert r.answers_updates["connect_queue"] == ["slack"]


def test_tools_selected_slack_connected_jira_github_queues_pm_unsupported_only() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_TOOLS,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    action = {
        "type": "tools_selected",
        "tools": {
            "engineering": ["github"],
            "pm": ["jira"],
            "communication": ["slack"],
            "docs": [],
        },
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a, slack_connected=True)
    assert r.next_step == STEP_UNSUPPORTED_MANDATORY_TOOLS
    assert r.answers_updates["unsupported_mandatory_sections"] == ["pm"]
    assert r.answers_updates["connect_queue"] == []


def test_unsupported_mandatory_tools_idle_stays_put() -> None:
    r = handle_turn(STEP_UNSUPPORTED_MANDATORY_TOOLS, "hello", None, {})
    assert r.next_step == STEP_UNSUPPORTED_MANDATORY_TOOLS
    assert r.answers_updates == {}


def test_tools_selected_teams_jira_gitlab_all_three_mandatory_unsupported() -> None:
    a = {
        "profile_phase": PROFILE_PHASE_TOOLS,
        "profile": {"name": "Ada", "role": "Founder"},
        "company": {"name": "Acme", "size": "5-15"},
    }
    action = {
        "type": "tools_selected",
        "tools": {
            "engineering": ["gitlab"],
            "pm": ["jira"],
            "communication": ["discord"],
            "docs": [],
        },
    }
    r = handle_turn(STEP_CHAT_PROFILE, None, action, a)
    assert r.next_step == STEP_UNSUPPORTED_MANDATORY_TOOLS
    assert r.answers_updates["unsupported_mandatory_sections"] == ["communication", "pm", "engineering"]
    assert r.answers_updates["connect_queue"] == []


def test_tools_selected_moves_to_connect_pm_with_tools_merged() -> None:
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
    assert r.next_step == STEP_CONNECT_PROJECT_MANAGEMENT
    assert r.answers_updates["profile_phase"] == PROFILE_PHASE_DONE
    assert "github" in r.answers_updates["tools"]["engineering"]
    assert "linear" in r.answers_updates["tools"]["pm"]
    assert r.answers_updates["connect_queue"] == ["linear", "github", "slack"]
    assert r.answers_updates.get("unsupported_mandatory_sections") == []


def test_tools_selected_skips_already_connected_slack() -> None:
    """Slack already linked: queue drops Slack; Linear and GitHub OAuth remain."""
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
    assert r.next_step == STEP_CONNECT_PROJECT_MANAGEMENT
    assert r.answers_updates["connect_queue"] == ["linear", "github"]


def test_tools_selected_all_three_connectors_linked_goes_slack_stakeholders() -> None:
    """Slack, Linear, and GitHub already linked: nothing left to OAuth in onboarding."""
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
    r = handle_turn(
        STEP_CHAT_PROFILE,
        None,
        action,
        a,
        slack_connected=True,
        linear_connected=True,
        github_connected=True,
    )
    assert r.next_step == STEP_SLACK_STAKEHOLDERS
    assert r.answers_updates["connect_queue"] == []


def test_connect_communication_message_with_github_in_tools_finishes_queue() -> None:
    """Queue is communication-only; GitHub in tools does not appear in connect_queue."""
    a = {
        "tools": {
            "engineering": ["github"],
            "pm": [],
            "communication": [],
            "docs": [],
        }
    }
    r = handle_turn(STEP_CONNECT_COMMUNICATION, "ok", None, a)
    assert r.next_step == STEP_SCANNING
    assert r.answers_updates["connect_queue"] == []


def test_connect_slack_no_live_tools_goes_scanning() -> None:
    a = {"tools": {"engineering": [], "pm": [], "communication": ["slack"], "docs": []}}
    r = handle_turn(STEP_CONNECT_COMMUNICATION, "continue", None, a)
    assert r.next_step == STEP_SLACK_STAKEHOLDERS


def test_connect_communication_linear_only_goes_scanning() -> None:
    a = {"tools": {"engineering": [], "pm": ["linear"], "communication": [], "docs": []}}
    r = handle_turn(STEP_CONNECT_COMMUNICATION, "go", None, a)
    assert r.next_step == STEP_SCANNING
    assert r.answers_updates["connect_queue"] == []


def test_admin_access_step_stays_put() -> None:
    r = handle_turn(STEP_ADMIN_ACCESS, "hello", None, {})
    assert r.next_step == STEP_ADMIN_ACCESS
    assert r.answers_updates == {}
