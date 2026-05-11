"""Start URL + complete GitHub App install / user OAuth callback."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.github.errors import (
    GitHubApiError,
    GitHubConnectorNotConfiguredError,
    GitHubInstallationConflictError,
    GitHubInstallMissingError,
    GitHubInstallStateMembershipError,
    GitHubUserOAuthError,
)
from vector.domains.cortex.connectors.github.http_client import (
    GitHubUserTokenExchange,
    exchange_github_user_code,
    fetch_github_installation,
)
from vector.domains.cortex.connectors.github.install_state import (
    GitHubInstallStateClaims,
    create_install_state_token,
    parse_install_state_token,
)
from vector.domains.cortex.connectors.github.return_path import sanitize_github_install_return_to
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.settings import Settings

GITHUB_INSTALL_NEW_URL_TEMPLATE = "https://github.com/apps/{slug}/installations/new"


def github_install_callback_url(settings: Settings) -> str:
    if settings.github_user_callback_url.strip():
        return settings.github_user_callback_url.strip().rstrip("/")
    return f"{settings.github_api_public_base_url.rstrip('/')}/connectors/github/callback"


def github_connector_configured(settings: Settings) -> bool:
    return bool(
        settings.github_app_id.strip()
        and settings.github_app_private_key.strip()
        and settings.github_app_slug.strip()
        and settings.github_client_id.strip()
        and settings.github_client_secret.strip()
    )


def start_github_install_url(
    settings: Settings,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    return_to: str | None = None,
) -> str:
    if not github_connector_configured(settings):
        raise GitHubConnectorNotConfiguredError("github app is not configured")
    safe = sanitize_github_install_return_to(return_to)
    state = create_install_state_token(settings, tenant_id, user_id, return_to=safe)
    base = GITHUB_INSTALL_NEW_URL_TEMPLATE.format(slug=settings.github_app_slug.strip())
    return f"{base}?state={quote(state, safe='')}"


def _account_from_installation_payload(payload: dict[str, Any]) -> tuple[int, str, str]:
    raw_account = payload.get("account")
    if not isinstance(raw_account, dict):
        raise GitHubApiError("installation response missing account")
    account_id = raw_account.get("id")
    login = raw_account.get("login")
    type_ = raw_account.get("type")
    if not isinstance(account_id, int) or not isinstance(login, str) or not isinstance(type_, str):
        raise GitHubApiError("installation account has unexpected shape")
    return account_id, login, type_


def complete_github_install(
    session: Session,
    settings: Settings,
    *,
    code: str,
    state: str,
    installation_id: int | None,
    exchange_code: Callable[[Settings, str], GitHubUserTokenExchange] | None = None,
    fetch_installation: Callable[[Settings, int], dict[str, Any]] | None = None,
) -> tuple[gh_repo.GithubTenantLink, str | None]:
    if not github_connector_configured(settings):
        raise GitHubConnectorNotConfiguredError("github app is not configured")
    if installation_id is None:
        raise GitHubInstallMissingError("missing installation_id")
    claims: GitHubInstallStateClaims = parse_install_state_token(settings, state)
    redirect_after = claims.return_to
    if tenancy_repo.get_membership_for_user_tenant(
        session,
        claims.user_id,
        claims.tenant_id,
    ) is None:
        raise GitHubInstallStateMembershipError()

    tenant_id = claims.tenant_id
    user_id = claims.user_id

    exchange_fn = exchange_code or exchange_github_user_code
    fetch_fn = fetch_installation or fetch_github_installation

    try:
        exchange_fn(settings, code)
    except GitHubUserOAuthError:
        raise

    try:
        inst_payload = fetch_fn(settings, installation_id)
    except GitHubApiError:
        raise

    inst_id_raw = inst_payload.get("id")
    if inst_id_raw != installation_id:
        raise GitHubApiError("installation id mismatch")

    holder = gh_repo.get_github_connection_for_installation(session, installation_id)
    if holder is not None and holder.connection.tenant_id != tenant_id:
        raise GitHubInstallationConflictError()

    account_id, account_login, account_type = _account_from_installation_payload(inst_payload)
    link = gh_repo.upsert_github_connection(
        session,
        tenant_id=tenant_id,
        installation_id=installation_id,
        account_id=account_id,
        account_login=account_login,
        account_type=account_type,
        connected_by_user_id=user_id,
    )
    return link, redirect_after
