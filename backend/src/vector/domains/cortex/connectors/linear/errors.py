"""Linear connector domain errors."""


class LinearConnectorNotConfiguredError(Exception):
    """Linear OAuth client id/secret not set."""


class InvalidLinearOAuthStateError(Exception):
    """Signed OAuth state invalid or expired."""


class LinearOAuthError(Exception):
    """Token exchange or Linear API failure."""


class LinearInstallStateMembershipError(Exception):
    """Callback state valid but user is not a member of the tenant."""
