"""Slack OAuth error redirects preserve SPA return_to from signed state."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from vector.domains.cortex.connectors.slack.install_state import SlackOAuthStateClaims
from vector.domains.cortex.connectors.slack.oauth_flow import slack_oauth_error_frontend_redirect_url


def test_slack_oauth_error_redirect_falls_back_to_root_when_no_state() -> None:
    settings = MagicMock()
    settings.frontend_url = "http://localhost:5173"
    url = slack_oauth_error_frontend_redirect_url(settings, None, "oauth")
    assert url == "http://localhost:5173/?slack_error=oauth"


def test_slack_oauth_error_redirect_preserves_return_to_from_state() -> None:
    settings = MagicMock()
    settings.frontend_url = "http://localhost:5173"
    tid = uuid.uuid4()
    uid = uuid.uuid4()
    with patch(
        "vector.domains.cortex.connectors.slack.oauth_flow.parse_slack_oauth_state_token",
        return_value=SlackOAuthStateClaims(tenant_id=tid, user_id=uid, return_to="/app/onboarding"),
    ):
        url = slack_oauth_error_frontend_redirect_url(settings, "signed-state", "workspace_taken")
    assert url == "http://localhost:5173/app/onboarding?slack_error=workspace_taken"
