"""GitHub REST routes for local mock."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from starlette.requests import Request

from mock_connectors.github_mock import dataset_generator as gh_gen
from mock_connectors.github_mock.pagination import github_link_header


def build_github_router(get_gh: Callable[[], dict[str, Any]]) -> APIRouter:
    r = APIRouter()

    @r.get("/installation/repositories")
    def installation_repositories(
        request: Request,
        page: int = 1,
        per_page: int = 100,
        authorization: str | None = Header(None),
    ) -> JSONResponse:
        del authorization
        gh = get_gh()
        payload = gh_gen.installation_repositories_payload(gh, page=page, per_page=per_page)
        total = len(gh["repos"])
        headers = github_link_header(request, page=page, per_page=per_page, total_items=total)
        return JSONResponse(payload, headers=headers)

    @r.get("/repos/{owner}/{repo_name}/pulls")
    def list_pulls(
        request: Request,
        owner: str,
        repo_name: str,
        state: str = "all",
        sort: str = "updated",
        direction: str = "desc",
        page: int = 1,
        per_page: int = 100,
    ) -> JSONResponse:
        del state, sort, direction
        gh = get_gh()
        payload, total = gh_gen.pulls_for_repo_with_total(
            gh, owner, repo_name, page=page, per_page=per_page
        )
        headers = github_link_header(request, page=page, per_page=per_page, total_items=total)
        return JSONResponse(payload, headers=headers)

    @r.get("/repos/{owner}/{repo_name}/pulls/{n}/commits")
    def list_pull_commits(
        request: Request,
        owner: str,
        repo_name: str,
        n: int,
        page: int = 1,
        per_page: int = 100,
    ) -> JSONResponse:
        gh = get_gh()
        payload, total = gh_gen.pull_commits_for_with_total(
            gh,
            owner,
            repo_name,
            n,
            page=page,
            per_page=per_page,
        )
        headers = github_link_header(request, page=page, per_page=per_page, total_items=total)
        return JSONResponse(payload, headers=headers)

    @r.get("/repos/{owner}/{repo_name}/issues")
    def list_issues(
        request: Request,
        owner: str,
        repo_name: str,
        page: int = 1,
        per_page: int = 100,
        since: str | None = None,
    ) -> JSONResponse:
        del since
        gh = get_gh()
        payload, total = gh_gen.issues_for_repo_with_total(
            gh, owner, repo_name, page=page, per_page=per_page
        )
        headers = github_link_header(request, page=page, per_page=per_page, total_items=total)
        return JSONResponse(payload, headers=headers)

    @r.get("/repos/{owner}/{repo_name}/commits")
    def list_commits(
        request: Request,
        owner: str,
        repo_name: str,
        sha: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> JSONResponse:
        gh = get_gh()
        payload, total = gh_gen.commits_for_repo_with_total(
            gh,
            owner,
            repo_name,
            page=page,
            per_page=per_page,
            sha=sha,
        )
        headers = github_link_header(request, page=page, per_page=per_page, total_items=total)
        return JSONResponse(payload, headers=headers)

    @r.post("/app/installations/{installation_id}/access_tokens")
    def installation_token(
        installation_id: int,
        authorization: str | None = Header(None),
    ) -> JSONResponse:
        del installation_id, authorization
        gh = get_gh()
        return JSONResponse(
            {
                "token": gh.get("installation_token", "mock-gh-install-token-vector"),
                "expires_at": "2099-01-01T00:00:00Z",
            },
        )

    @r.get("/app/installations/{installation_id}")
    def installation_get(installation_id: int) -> JSONResponse:
        del installation_id
        return JSONResponse({"id": 12345, "account": {"login": "nexora", "type": "Organization"}})

    return r
