"""GitHub connector domain errors."""


class GitHubConnectorNotConfiguredError(Exception):
    """Missing GitHub App env (client id, private key, …)."""


class InvalidGitHubInstallStateError(Exception):
    """Signed install `state` missing, tampered, or expired."""


class GitHubInstallStateMembershipError(Exception):
    """User in `state` is not a member of the tenant (stale or forged state)."""


class GitHubUserOAuthError(Exception):
    """Token exchange failed or GitHub returned an error payload."""


class GitHubInstallationConflictError(Exception):
    """Installation already linked to a different tenant."""


class GitHubApiError(Exception):
    """GitHub REST error when fetching installation metadata."""


class GitHubInstallMissingError(Exception):
    """Callback did not include installation_id (required for this flow)."""
