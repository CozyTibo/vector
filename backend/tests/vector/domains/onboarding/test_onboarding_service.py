"""Tests for onboarding chat orchestration (idle POST, idempotency)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from vector.contracts.onboarding import OnboardingChatRequest
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.domains.onboarding.constants import STATUS_IN_PROGRESS, STEP_CHAT_PROFILE
from vector.domains.onboarding.onboarding_service import process_onboarding_chat


@pytest.fixture
def claims() -> SessionClaims:
    return SessionClaims(user_id=uuid.uuid4(), tenant_id=uuid.uuid4())


def test_empty_post_after_name_phase_is_idempotent_no_commit_path(claims: SessionClaims) -> None:
    """Refresh-style POST with message '' at tools phase must not run the LLM pipeline."""
    session = MagicMock()
    row = MagicMock()
    row.status = STATUS_IN_PROGRESS
    row.current_step = STEP_CHAT_PROFILE
    row.answers_json = {
        "profile_phase": "tools",
        "profile": {"name": "Tibo"},
        "company": {"name": "Acme"},
    }

    body = OnboardingChatRequest(message="")

    with patch(
        "vector.domains.onboarding.onboarding_service.ob_repo.get_or_create_onboarding",
        return_value=row,
    ):
        with patch(
            "vector.domains.onboarding.onboarding_service.ob_repo.onboarding_messages_table_exists",
            return_value=False,
        ):
            out = process_onboarding_chat(session, claims, body)

    assert out.step == STEP_CHAT_PROFILE
    assert out.answers == row.answers_json
    assert "tools" in out.assistant_message.lower() or "pick" in out.assistant_message.lower()
    session.commit.assert_not_called()
