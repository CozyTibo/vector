from vector.domains.manager_onboarding.constants import SCOPE_JUST_ME, SCOPE_OTHER_MANAGERS
from vector.domains.manager_onboarding.engine.requirements import (
    REQ_CHANNELS,
    REQ_KPIS,
    REQ_PEER_HANDLES,
    REQ_REPORTS_TO,
    REQ_SCOPE_INTENT,
    REQ_TEAM_SCOPE,
    missing_requirements,
    primary_requirement,
)


def test_missing_starts_scope() -> None:
    assert missing_requirements({}) == [REQ_SCOPE_INTENT]
    assert primary_requirement({}) == REQ_SCOPE_INTENT


def test_peer_empty_list_satisfies_other_managers_step() -> None:
    """Explicit [] means "no other managers" — advance to team scope."""
    a = {"scope_intent": SCOPE_OTHER_MANAGERS, "peer_slack_user_ids": []}
    assert missing_requirements(a) == [REQ_TEAM_SCOPE]


def test_team_members_empty_list_satisfied() -> None:
    a = {
        "scope_intent": SCOPE_JUST_ME,
        "team_scope": "x",
        "team_member_slack_ids": [],
    }
    assert missing_requirements(a) == [REQ_CHANNELS]


def test_channels_empty_list_satisfied_when_not_skipped() -> None:
    a = {
        "scope_intent": SCOPE_JUST_ME,
        "team_scope": "x",
        "team_member_slack_ids": ["U1"],
        "observed_channel_ids": [],
    }
    assert missing_requirements(a) == [REQ_REPORTS_TO]


def test_team_scope_after_just_me() -> None:
    a = {"scope_intent": SCOPE_JUST_ME}
    assert primary_requirement(a) == REQ_TEAM_SCOPE


def test_completed_minimal_no_reports() -> None:
    a = {
        "scope_intent": SCOPE_JUST_ME,
        "team_scope": "x",
        "team_member_slack_ids": ["U1"],
        "observed_channel_ids": ["C1"],
        "reports_to_yes": False,
        "kpi_expectations": "",
    }
    assert missing_requirements(a) == []


def test_kpis_when_reports_yes() -> None:
    a = {
        "scope_intent": SCOPE_JUST_ME,
        "team_scope": "x",
        "team_member_slack_ids": ["U1"],
        "observed_channel_ids": ["C1"],
        "reports_to_yes": True,
        "reports_to_slack_ids": ["U2"],
        "kpi_expectations": "",
    }
    assert primary_requirement(a) == REQ_KPIS
