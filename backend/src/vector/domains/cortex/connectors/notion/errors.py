"""Notion connector domain errors."""


class NotionConnectorNotConfiguredError(Exception):
    """Notion OAuth client id/secret not set."""


class InvalidNotionOAuthStateError(Exception):
    """Signed OAuth state invalid or expired."""


class NotionOAuthError(Exception):
    """Token exchange or Notion API failure."""


class NotionInstallStateMembershipError(Exception):
    """Callback state valid but user is not a member of the tenant."""
