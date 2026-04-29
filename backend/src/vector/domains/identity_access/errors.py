"""Domain errors for identity / tenant flows."""


class IdentityAccessError(Exception):
    """Base for identity_access."""


class OAuthNotConfiguredError(IdentityAccessError):
    """OAuth client credentials missing."""


class InvalidOAuthStateError(IdentityAccessError):
    """CSRF state or PKCE cookie invalid or expired."""


class GoogleOAuthError(IdentityAccessError):
    """Token exchange or ID token verification failed."""


class NoMembershipError(IdentityAccessError):
    """User has no tenant membership."""


class SessionInvalidError(IdentityAccessError):
    """Session JWT missing or invalid."""


class EmailAlreadyRegisteredError(IdentityAccessError):
    """Sign-up attempted for an existing email."""


class InvalidCredentialsError(IdentityAccessError):
    """Wrong email/password or account cannot use password login."""


class WeakPasswordError(IdentityAccessError):
    """Password does not meet policy."""


class InvalidPasswordResetTokenError(IdentityAccessError):
    """Unknown, expired, or already-used password reset token."""
