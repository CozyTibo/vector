"""Unit tests for onboarding connector OAuth chat log lines."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from vector.domains.onboarding.connector_connected_chat_log import append_connector_connected_user_line


def test_append_skips_when_return_to_not_onboarding() -> None:
    session = MagicMock()
    with patch("vector.domains.onboarding.connector_connected_chat_log.ob_repo") as mock_ob:
        append_connector_connected_user_line(
            session,
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            return_to="/app/settings",
            tool_label="Linear",
        )
        mock_ob.onboarding_messages_table_exists.assert_not_called()


def test_append_skips_when_messages_table_missing() -> None:
    session = MagicMock()
    with patch("vector.domains.onboarding.connector_connected_chat_log.ob_repo") as mock_ob:
        mock_ob.onboarding_messages_table_exists.return_value = False
        append_connector_connected_user_line(
            session,
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            return_to="/app/onboarding",
            tool_label="GitHub",
        )
        mock_ob.get_onboarding_for_tenant.assert_not_called()
