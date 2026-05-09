"""Outbound HTTP to GitHub (token exchange + installation API)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from vector.domains.cortex.connectors.github.app_jwt import create_github_app_jwt
from vector.domains.cortex.connectors.github.errors import GitHubApiError, GitHubUserOAuthError
from vector.settings import Settings

GITHUB_OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"


def _github_rest_get(
    settings: Settings,
    installation_access_token: str,
    *,
    path: str,
    params: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> httpx.Response:
    base = settings.github_rest_api_base_url().rstrip("/")
    p = path if path.startswith("/") else f"/{path}"
    url = f"{base}{p}"
    try:
        resp = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {installation_access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params=params or None,
            timeout=timeout,
        )
    except httpx.RequestError as e:
        raise GitHubApiError(f"github request failed ({p}): {e}") from e
    if resp.status_code == 429:
        raise GitHubApiError(f"github rate limited (429) for {p}") from None
    if resp.is_error:
        snippet = (resp.text or "").replace("\n", " ")[:400]
        raise GitHubApiError(
            f"github {p} http {resp.status_code}" + (f" — {snippet}" if snippet else ""),
        ) from None
    return resp


def _github_rest_array(
    settings: Settings,
    installation_access_token: str,
    *,
    path: str,
    params: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> list[dict[str, Any]]:
    resp = _github_rest_get(
        settings,
        installation_access_token,
        path=path,
        params=params,
        timeout=timeout,
    )
    try:
        data = resp.json()
    except ValueError:
        raise GitHubApiError(f"github {path} not json (http {resp.status_code})") from None
    if not isinstance(data, list):
        raise GitHubApiError(f"github {path} response not array")
    return [x for x in data if isinstance(x, dict)]


def _github_rest_object(
    settings: Settings,
    installation_access_token: str,
    *,
    path: str,
    params: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    resp = _github_rest_get(
        settings,
        installation_access_token,
        path=path,
        params=params,
        timeout=timeout,
    )
    try:
        data = resp.json()
    except ValueError:
        raise GitHubApiError(f"github {path} not json (http {resp.status_code})") from None
    if not isinstance(data, dict):
        raise GitHubApiError(f"github {path} response not object")
    return data


@dataclass(frozen=True)
class GitHubUserTokenExchange:
    access_token: str
    refresh_token: str | None
    expires_in: int | None


def exchange_github_user_code(settings: Settings, code: str) -> GitHubUserTokenExchange:
    """OAuth: authorization code → user access token (GitHub App credentials)."""
    try:
        resp = httpx.post(
            GITHUB_OAUTH_ACCESS_TOKEN_URL,
            headers={
                "Accept": "application/json",
            },
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            timeout=30.0,
        )
    except httpx.RequestError as e:
        raise GitHubUserOAuthError(f"github token request failed: {e}") from e
    if resp.is_error:
        raise GitHubUserOAuthError(f"github token http {resp.status_code}") from None
    try:
        body = resp.json()
    except ValueError:
        raise GitHubUserOAuthError(
            f"github token response not json (http {resp.status_code})",
        ) from None
    err = body.get("error")
    if err:
        desc = body.get("error_description", err)
        raise GitHubUserOAuthError(str(desc))
    token = body.get("access_token")
    if not token or not isinstance(token, str):
        raise GitHubUserOAuthError("missing access_token in github response")
    refresh = body.get("refresh_token")
    expires_in = body.get("expires_in")
    exp_int = int(expires_in) if isinstance(expires_in, int) else None
    refresh_s = refresh if isinstance(refresh, str) else None
    return GitHubUserTokenExchange(
        access_token=token,
        refresh_token=refresh_s,
        expires_in=exp_int,
    )


def fetch_github_installation(
    settings: Settings,
    installation_id: int,
) -> dict[str, Any]:
    """GET /app/installations/{id} with app JWT."""
    app_jwt = create_github_app_jwt(settings)
    base = settings.github_rest_api_app_install_base_url()
    url = f"{base}/app/installations/{installation_id}"
    try:
        resp = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
    except httpx.RequestError as e:
        raise GitHubApiError(f"github installation request failed: {e}") from e
    if resp.is_error:
        snippet = (resp.text or "").replace("\n", " ")[:400]
        raise GitHubApiError(
            f"github installation http {resp.status_code}"
            + (f" — {snippet}" if snippet else ""),
        ) from None
    try:
        data = resp.json()
    except ValueError:
        raise GitHubApiError(
            f"github installation response not json (http {resp.status_code})",
        ) from None
    if not isinstance(data, dict):
        raise GitHubApiError("invalid github installation json")
    return data


def create_github_installation_access_token(
    settings: Settings,
    installation_id: int,
) -> str:
    """POST /app/installations/{id}/access_tokens — returns short-lived installation token."""
    app_jwt = create_github_app_jwt(settings)
    base = settings.github_rest_api_base_url()
    url = f"{base}/app/installations/{installation_id}/access_tokens"
    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
    except httpx.RequestError as e:
        raise GitHubApiError(f"github installation token request failed: {e}") from e
    if resp.is_error:
        snippet = (resp.text or "").replace("\n", " ")[:400]
        raise GitHubApiError(
            f"github installation token http {resp.status_code}"
            + (f" — {snippet}" if snippet else ""),
        ) from None
    try:
        data = resp.json()
    except ValueError:
        raise GitHubApiError(
            f"github installation token response not json (http {resp.status_code})",
        ) from None
    token = data.get("token")
    if not isinstance(token, str) or not token:
        raise GitHubApiError("github installation token missing token field")
    return token


def list_installation_repositories_page(
    settings: Settings,
    installation_access_token: str,
    *,
    page: int,
    per_page: int = 100,
) -> tuple[list[dict[str, Any]], int | None]:
    """GET /installation/repositories for one ``page`` (installation bearer token)."""
    base = settings.github_rest_api_base_url().rstrip("/")
    url = f"{base}/installation/repositories"
    try:
        resp = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {installation_access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params={"per_page": min(per_page, 100), "page": max(page, 1)},
            timeout=60.0,
        )
    except httpx.RequestError as e:
        raise GitHubApiError(f"github installation repositories request failed: {e}") from e
    if resp.is_error:
        snippet = (resp.text or "").replace("\n", " ")[:400]
        raise GitHubApiError(
            f"github installation repositories http {resp.status_code}"
            + (f" — {snippet}" if snippet else ""),
        ) from None
    try:
        data = resp.json()
    except ValueError:
        raise GitHubApiError(
            f"github installation repositories not json (http {resp.status_code})",
        ) from None
    if not isinstance(data, dict):
        raise GitHubApiError("invalid github installation repositories json")
    repos_raw = data.get("repositories")
    if not isinstance(repos_raw, list):
        raise GitHubApiError("github installation repositories missing repositories array")
    repos: list[dict[str, Any]] = [x for x in repos_raw if isinstance(x, dict)]
    total = data.get("total_count")
    total_int = int(total) if isinstance(total, int) else None
    return repos, total_int


def list_repo_pulls(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    per_page: int = 30,
    state: str = "all",
) -> list[dict[str, Any]]:
    """GET /repos/{owner}/{repo}/pulls first page (compat wrapper)."""
    return list_repo_pulls_page(
        settings,
        installation_access_token,
        owner=owner,
        repo=repo,
        page=1,
        per_page=per_page,
        state=state,
    )


def list_repo_pulls_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    page: int,
    per_page: int = 30,
    state: str = "all",
) -> list[dict[str, Any]]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/pulls",
        params={
            "state": state,
            "per_page": min(per_page, 100),
            "page": max(page, 1),
            "sort": "updated",
            "direction": "desc",
        },
    )


def list_pull_reviews_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    pull_number: int,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/pulls/{pull_number}/reviews",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )


def list_pull_review_comments_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    pull_number: int,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/pulls/{pull_number}/comments",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )


def list_pull_issue_comments_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    pull_number: int,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/issues/{pull_number}/comments",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )


def list_repo_commits_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/commits",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )


def list_repo_check_runs_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    ref: str,
    page: int,
    per_page: int = 100,
) -> tuple[list[dict[str, Any]], int | None]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    obj = _github_rest_object(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/commits/{ref}/check-runs",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )
    rows_raw = obj.get("check_runs")
    rows = [x for x in rows_raw if isinstance(x, dict)] if isinstance(rows_raw, list) else []
    total = obj.get("total_count")
    return rows, int(total) if isinstance(total, int) else None


def list_repo_workflow_runs_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    page: int,
    per_page: int = 100,
) -> tuple[list[dict[str, Any]], int | None]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    obj = _github_rest_object(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/actions/runs",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )
    rows_raw = obj.get("workflow_runs")
    rows = [x for x in rows_raw if isinstance(x, dict)] if isinstance(rows_raw, list) else []
    total = obj.get("total_count")
    return rows, int(total) if isinstance(total, int) else None


def list_repo_deployments_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/deployments",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )


def list_deployment_statuses_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    deployment_id: int,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/deployments/{deployment_id}/statuses",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )


def list_repo_branches_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/branches",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )


def list_repo_tags_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/tags",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )


def list_repo_commit_comments_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    """List commit comments for a repository (not PR review comments)."""
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/comments",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )


def list_repo_releases_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/releases",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )


def list_repo_issues_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/issues",
        params={
            "per_page": min(per_page, 100),
            "page": max(page, 1),
            "state": "all",
        },
    )


def list_repo_issue_timeline_page(
    settings: Settings,
    installation_access_token: str,
    *,
    owner: str,
    repo: str,
    issue_number: int,
    page: int,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    """GET /repos/{owner}/{repo}/issues/{issue_number}/timeline (issue or PR number)."""
    owner_s = owner.strip().strip("/")
    repo_s = repo.strip().strip("/")
    return _github_rest_array(
        settings,
        installation_access_token,
        path=f"/repos/{owner_s}/{repo_s}/issues/{issue_number}/timeline",
        params={"per_page": min(per_page, 100), "page": max(page, 1)},
    )


def list_installation_repositories_first_page(
    settings: Settings,
    installation_id: int,
    *,
    per_page: int = 50,
) -> tuple[list[dict[str, Any]], int | None]:
    """GET /installation/repositories (first page) using an installation access token.

    Returns repository dicts from the GitHub API (``repositories`` array) and ``total_count`` when
    present.
    """
    token = create_github_installation_access_token(settings, installation_id)
    return list_installation_repositories_page(settings, token, page=1, per_page=per_page)
