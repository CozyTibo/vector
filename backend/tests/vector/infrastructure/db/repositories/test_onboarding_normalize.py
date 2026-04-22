"""Tests for legacy onboarding row coercion (removed GitHub/Linear steps)."""

from __future__ import annotations

import uuid

from vector.domains.onboarding.constants import (
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STEP_CONNECT_COMMUNICATION,
    STEP_CONNECT_ENGINEERING,
    STEP_SCANNING,
)
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.repositories.onboarding import normalize_onboarding_row_removed_steps


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
