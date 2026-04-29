"""Request and complete password reset via one-time token (email link)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from vector.domains.identity_access.errors import InvalidPasswordResetTokenError
from vector.domains.identity_access.services.passwords import hash_password
from vector.infrastructure.db.models.password_reset_token import PasswordResetToken
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.infrastructure.email.password_reset import enqueue_password_reset_email
from vector.settings import Settings

_RESET_TTL = timedelta(hours=1)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def request_password_reset(session: Session, settings: Settings, *, email: str) -> None:
    """
    If a password-based account exists, create a token and enqueue reset email.
    Always safe to call (no indication whether email exists).
    """
    if not settings.email_is_configured:
        return

    normalized = email.strip().lower()
    user = tenancy_repo.get_user_by_email(session, normalized)
    if user is None or not user.password_hash:
        return

    session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    raw = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw)
    expires_at = datetime.now(tz=UTC) + _RESET_TTL
    session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )
    session.flush()

    reset_url = (
        f"{settings.frontend_url.rstrip('/')}/login/reset-password?token={quote(raw, safe='')}"
    )
    ttl_hours = max(1, int(_RESET_TTL.total_seconds() // 3600))
    enqueue_password_reset_email(
        to=normalized,
        reset_url=reset_url,
        email_hint=normalized,
        ttl_hours=ttl_hours,
    )


def reset_password_with_token(session: Session, *, token: str, new_password: str) -> None:
    """Set a new password when token is valid; raises InvalidPasswordResetTokenError otherwise."""
    raw = (token or "").strip()
    if not raw:
        raise InvalidPasswordResetTokenError("invalid reset token")
    th = _hash_token(raw)
    row = session.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == th))
    now = datetime.now(tz=UTC)
    if row is None or row.used_at is not None or row.expires_at < now:
        raise InvalidPasswordResetTokenError("invalid reset token")

    user = tenancy_repo.get_user_by_id(session, row.user_id)
    if user is None:
        raise InvalidPasswordResetTokenError("invalid reset token")

    user.password_hash = hash_password(new_password)
    session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
