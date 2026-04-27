"""Calls connector domain errors."""


class CallsConnectorNotConfiguredError(Exception):
    """Calls OAuth client id/secret not set."""


class InvalidCallsOAuthStateError(Exception):
    """Signed OAuth state invalid or expired."""


class CallsOAuthError(Exception):
    """Token exchange or provider API failure."""


class CallsInstallStateMembershipError(Exception):
    """Callback state valid but user is not a member of the tenant."""
