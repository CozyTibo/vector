"""Tests for legacy onboarding row coercion (removed GitHub/Linear steps)."""

from __future__ import annotations

import uuid

from vector.domains.onboarding.constants import (
    PROFILE_PHASE_CONNECTORS_INTRO,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STEP_CHAT_PROFILE,
    STEP_CONNECT_COMMUNICATION,
    STEP_CONNECT_ENGINEERING,
    STEP_SCANNING,
    STEP_SLACK_COLLABORATORS,
    STEP_SLACK_STAKEHOLDERS,
    STEP_THANK_YOU,
)
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.repositories.onboarding import (
    normalize_onboarding_row_removed_steps,
    normalize_vector_manager_access_mode_in_place,
    normalize_workspace_manager_teams_in_place,
)


def test_normalize_obsolete_github_step_maps_to_connect_engineering() -> None:
    row = OnboardingState(
        tenant_id=uuid.uuid4(),
        status=STATUS_IN_PROGRESS,
        current_step="CONNECT_GITHUB",
        answers_json={"connect_queue": ["github"], "connect_plan": ["github"]},
        version=3,
    )
    normalize_onboarding_row_removed_steps(row)
    assert row.current_step == STEP_CONNECT_ENGINEERING
    assert row.answers_json["connect_queue"] == ["github"]
    assert row.answers_json["connect_plan"] == ["github"]
    assert row.version == 4


def test_normalize_obsolete_step_with_slack_pending_goes_connect_communication() -> None:
    row = OnboardingState(
        tenant_id=uuid.uuid4(),
        status=STATUS_IN_PROGRESS,
        current_step="CONNECT_LINEAR",
        answers_json={"connect_queue": ["slack", "github"]},
        version=1,
    )
    normalize_onboarding_row_removed_steps(row)
    assert row.current_step == STEP_CONNECT_COMMUNICATION
    assert row.answers_json["connect_queue"] == ["slack", "github"]
    assert row.version == 2


def test_normalize_obsolete_github_empty_queue_goes_scanning() -> None:
    row = OnboardingState(
        tenant_id=uuid.uuid4(),
        status=STATUS_IN_PROGRESS,
        current_step="CONNECT_GITHUB",
        answers_json={"connect_queue": [], "connect_plan": []},
        version=2,
    )
    normalize_onboarding_row_removed_steps(row)
    assert row.current_step == STEP_SCANNING
    assert row.version == 3


def test_normalize_profile_phase_size_to_connectors_intro() -> None:
    row = OnboardingState(
        tenant_id=uuid.uuid4(),
        status=STATUS_IN_PROGRESS,
        current_step=STEP_CHAT_PROFILE,
        answers_json={"profile_phase": "size"},
        version=1,
    )
    normalize_onboarding_row_removed_steps(row)
    assert row.answers_json["profile_phase"] == PROFILE_PHASE_CONNECTORS_INTRO
    assert row.version == 2


def test_normalize_deprecated_slack_tail_with_stakeholders_marks_completed() -> None:
    row = OnboardingState(
        tenant_id=uuid.uuid4(),
        status=STATUS_IN_PROGRESS,
        current_step=STEP_SLACK_COLLABORATORS,
        answers_json={
            "slack_stakeholders": {"slack_user_ids": ["U123"], "mention_labels": ["@ada"]},
        },
        version=1,
    )
    normalize_onboarding_row_removed_steps(row)
    assert row.status == STATUS_COMPLETED
    assert row.current_step == STEP_THANK_YOU
    assert row.completed_at is not None
    assert row.version == 2


def test_normalize_vector_manager_access_mode_keeps_valid() -> None:
    answers: dict = {"vector_manager_access_mode": "company_wide"}
    normalize_vector_manager_access_mode_in_place(answers)
    assert answers["vector_manager_access_mode"] == "company_wide"


def test_normalize_vector_manager_access_mode_drops_invalid() -> None:
    answers: dict = {"vector_manager_access_mode": "nope"}
    normalize_vector_manager_access_mode_in_place(answers)
    assert "vector_manager_access_mode" not in answers


def test_normalize_workspace_manager_teams_preserves_access_scope() -> None:
    tid = str(uuid.uuid4())
    answers: dict = {
        "workspace_manager_teams": {
            "teams": [
                {
                    "id": tid,
                    "name": "Alex",
                    "access_scope": "all",
                    "manager_slack_user_id": "U1",
                    "members": [
                        {"slack_user_id": "U1", "username": "alex", "label": "Alex"},
                    ],
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Team",
                    "access_scope": "scoped",
                    "manager_slack_user_id": "U2",
                    "members": [
                        {"slack_user_id": "U2", "username": "bob", "label": "Bob"},
                        {"slack_user_id": "U3", "username": "c", "label": "C"},
                    ],
                },
            ],
        },
    }
    normalize_workspace_manager_teams_in_place(answers)
    teams = answers["workspace_manager_teams"]["teams"]
    assert teams[0]["access_scope"] == "all"
    assert teams[1]["access_scope"] == "scoped"


def test_normalize_deprecated_slack_tail_without_stakeholders_goes_stakeholders_step() -> None:
    row = OnboardingState(
        tenant_id=uuid.uuid4(),
        status=STATUS_IN_PROGRESS,
        current_step=STEP_SLACK_COLLABORATORS,
        answers_json={},
        version=1,
    )
    normalize_onboarding_row_removed_steps(row)
    assert row.status == STATUS_IN_PROGRESS
    assert row.current_step == STEP_SLACK_STAKEHOLDERS
    assert row.version == 2


def test_normalize_does_not_mutate_completed_rows() -> None:
    row = OnboardingState(
        tenant_id=uuid.uuid4(),
        status=STATUS_COMPLETED,
        current_step="CONNECT_GITHUB",
        answers_json={"connect_queue": ["github"]},
        version=5,
    )
    normalize_onboarding_row_removed_steps(row)
    assert row.current_step == "CONNECT_GITHUB"
    assert row.answers_json["connect_queue"] == ["github"]
    assert row.version == 5
