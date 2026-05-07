"""Slack OAuth domain errors."""


class SlackOAuthError(Exception):
    """Token exchange or Slack API returned an error."""


class InvalidSlackOAuthStateError(Exception):
    """Signed `state` missing, expired, or tampered."""


class SlackInstallStateMembershipError(Exception):
    """Token user does not belong to tenant in state."""


class SlackConnectorNotConfiguredError(Exception):
    """Slack client id/secret not set."""


class SlackWorkspaceConflictError(Exception):
    """Another tenant already owns this Slack workspace connection."""
