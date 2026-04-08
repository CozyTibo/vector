"""Unit tests for manager onboarding step ordering."""

from types import SimpleNamespace

from vector.domains.manager_onboarding.constants import (
    SCOPE_JUST_ME,
    SCOPE_OTHER_MANAGERS,
    STATUS_COMPLETED,
    STATUS_NEEDS_REVIEW,
    STEP_COMPLETED,
    STEP_Q1_SCOPE_INTENT,
    STEP_Q1B_PEER_HANDLES,
    STEP_Q2_TEAM_SCOPE,
    STEP_Q3_TEAM_MEMBERS,
    STEP_Q4_OBSERVED_CHANNELS,
    STEP_Q5_REPORTS_TO,
    STEP_Q5B_REPORTS_WHO,
    STEP_Q6_KPIS,
)
from vector.domains.manager_onboarding.service import (
    first_unanswered_step,
    reconcile_needs_review_if_manager_flow_complete,
)


def test_first_unanswered_starts_at_q1() -> None:
    assert first_unanswered_step({}) == STEP_Q1_SCOPE_INTENT


def test_q1b_when_other_managers_no_peers() -> None:
    assert (
        first_unanswered_step({"scope_intent": SCOPE_OTHER_MANAGERS, "peer_slack_user_ids": []})
        == STEP_Q1B_PEER_HANDLES
    )


def test_skips_q1b_for_just_me() -> None:
    assert first_unanswered_step({"scope_intent": SCOPE_JUST_ME}) == STEP_Q2_TEAM_SCOPE


def test_q5b_when_reports_yes_no_ids() -> None:
    assert (
        first_unanswered_step(
            {
                "scope_intent": SCOPE_JUST_ME,
                "team_scope": "x",
                "team_member_slack_ids": ["U1"],
                "observed_channel_ids": ["C1"],
                "reports_to_yes": True,
                "reports_to_slack_ids": [],
            }
        )
        == STEP_Q5B_REPORTS_WHO
    )


def test_completed_when_no_reports() -> None:
    assert (
        first_unanswered_step(
            {
                "scope_intent": SCOPE_JUST_ME,
                "team_scope": "x",
                "team_member_slack_ids": ["U1"],
                "observed_channel_ids": ["C1"],
                "reports_to_yes": False,
                "kpi_expectations": "",
            }
        )
        == STEP_COMPLETED
    )


def test_q4_skipped_empty_list_advances_to_q5() -> None:
    assert (
        first_unanswered_step(
            {
                "scope_intent": SCOPE_JUST_ME,
                "team_scope": "x",
                "team_member_slack_ids": ["U1"],
                "observed_channel_ids": [],
                "observed_channels_skipped": True,
            }
        )
        == STEP_Q5_REPORTS_TO
    )


def test_q6_when_reports_yes() -> None:
    assert (
        first_unanswered_step(
            {
                "scope_intent": SCOPE_JUST_ME,
                "team_scope": "x",
                "team_member_slack_ids": ["U1"],
                "observed_channel_ids": ["C1"],
                "reports_to_yes": True,
                "reports_to_slack_ids": ["U2"],
                "kpi_expectations": "",
            }
        )
        == STEP_Q6_KPIS
    )


def _complete_answers_no_reports() -> dict:
    return {
        "scope_intent": SCOPE_JUST_ME,
        "team_scope": "x",
        "team_member_slack_ids": ["U1"],
        "observed_channel_ids": ["C1"],
        "reports_to_yes": False,
        "kpi_expectations": "",
    }


def test_reconcile_clears_needs_review_when_step_and_answers_done() -> None:
    sess = SimpleNamespace(
        status=STATUS_NEEDS_REVIEW,
        current_step=STEP_COMPLETED,
        answers_json=_complete_answers_no_reports(),
        completed_at=None,
        version=3,
    )
    assert reconcile_needs_review_if_manager_flow_complete(sess) is True
    assert sess.status == STATUS_COMPLETED
    assert sess.completed_at is not None
    assert sess.version == 4


def test_reconcile_noop_when_step_not_completed() -> None:
    sess = SimpleNamespace(
        status=STATUS_NEEDS_REVIEW,
        current_step=STEP_Q6_KPIS,
        answers_json=_complete_answers_no_reports(),
        version=1,
    )
    assert reconcile_needs_review_if_manager_flow_complete(sess) is False
    assert sess.status == STATUS_NEEDS_REVIEW
    assert sess.version == 1
