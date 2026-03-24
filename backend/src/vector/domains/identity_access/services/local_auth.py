"""Email + password sign-up and sign-in."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vector.domains.identity_access.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)
from vector.domains.identity_access.services.passwords import hash_password, verify_password
from vector.domains.identity_access.services.provisioning import bootstrap_tenant_for_new_user
from vector.domains.identity_access.services.session_jwt import issue_session_token
from vector.infrastructure.db.models.user import User
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.settings import Settings

_BAD_CREDENTIALS = "invalid email or password"


def register_with_email_password(
    session: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
    full_name: str | None,
    company_name: str | None,
) -> str:
    """
    Create user (password), first tenant, owner membership; return session JWT.

    Raises EmailAlreadyRegisteredError if email exists.
    """
    normalized = email.strip().lower()
    if tenancy_repo.get_user_by_email(session, normalized):
        raise EmailAlreadyRegisteredError("email already registered")
    password_h = hash_password(password)
    user = User(email=normalized, full_name=full_name, password_hash=password_h)
    session.add(user)
    try:
        session.flush()
    except IntegrityError as e:
        raise EmailAlreadyRegisteredError("email already registered") from e
    _tenant, _membership = bootstrap_tenant_for_new_user(
        session,
        user=user,
        email=normalized,
        company_name=company_name,
    )
    return issue_session_token(settings, user.id, _tenant.id)


def login_with_email_password(
    session: Session,
    settings: Settings,
    *,
    email: str,
    password: str,
) -> str:
    normalized = email.strip().lower()
    user = tenancy_repo.get_user_by_email(session, normalized)
    if user is None or user.password_hash is None:
        raise InvalidCredentialsError(_BAD_CREDENTIALS)
    if not verify_password(user.password_hash, password):
        raise InvalidCredentialsError(_BAD_CREDENTIALS)
    memberships = tenancy_repo.list_memberships_for_user(session, user.id)
    if not memberships:
        raise InvalidCredentialsError(_BAD_CREDENTIALS)
    m0 = memberships[0]
    return issue_session_token(settings, user.id, m0.tenant_id)
