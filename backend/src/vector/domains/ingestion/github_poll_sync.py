"""GitHub App polling ingestion (Step 1) — resource-level envelopes only."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from vector.domains.connectors.github.http_client import create_github_installation_access_token
from vector.domains.ingestion.http_fetch import (
    FetchExecutor,
    FetchFatalError,
    FetchTransientError,
    raise_for_github_status,
)
from vector.domains.projections.github.resource_types import RT_PULL_REQUEST_COMMIT
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.infrastructure.db.repositories import ingestion as ing_repo
from vector.settings import Settings

_logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"

CONNECTOR = ing_repo.CONNECTOR_GITHUB
SOURCE_POLL = ing_repo.SOURCE_TRIGGER_POLL
API_INSTALLATION_REpos = "GET /installation/repositories"
API_LIST_PULLS = "GET /repos/{owner}/{repo}/pulls"
API_LIST_PULL_COMMITS = "GET /repos/{owner}/{repo}/pulls/{n}/commits"
API_LIST_ISSUES = "GET /repos/{owner}/{repo}/issues"
API_LIST_COMMITS = "GET /repos/{owner}/{repo}/commits"

RT_REPOSITORY = "github.repository"
RT_PULL_REQUEST = "github.pull_request"
RT_ISSUE = "github.issue"
RT_COMMIT = "github.commit"

SCOPE_INSTALL_REPOS = "github:installation_repositories"


class GitHubRepoNotFoundError(Exception):
    """Repo disappeared or is not visible to this installation."""


@dataclass(frozen=True)
class _RepoRef:
    full_name: str
    owner: str
    name: str
    default_branch: str
    raw: dict[str, Any]


def _norm_full_name(full_name: str) -> str:
    parts = full_name.split("/", 1)
    if len(parts) != 2:
        return full_name.lower()
    return f"{parts[0].lower()}/{parts[1]}"


def _pulls_scope(full_name: str) -> str:
    return f"github:pulls:{full_name}"


def _issues_scope(full_name: str) -> str:
    return f"github:issues:{full_name}"


def _commits_scope(full_name: str) -> str:
    return f"github:commits:{full_name}"


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_json(
    executor: FetchExecutor,
    path: str,
    token: str,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    return executor.request(
        "GET",
        f"{GITHUB_API_BASE}{path}",
        headers=_github_headers(token),
        params=params or {},
    )


def _flush_batch(
    session: Session,
    run: IngestionRun,
    batch: list[dict[str, Any]],
    stats: dict[str, int],
) -> None:
    if not batch:
        return
    n = ing_repo.insert_raw_records_ignore_conflict(
        session,
        run=run,
        connector=CONNECTOR,
        source_trigger=SOURCE_POLL,
        batch=batch,
    )
    stats["records_written"] = stats.get("records_written", 0) + n
    session.commit()


def run_github_poll_ingestion_for_tenant(
    session: Session,
    settings: Settings,
    tenant_id: uuid.UUID,
) -> IngestionRun:
    """Poll GitHub for the tenant’s linked installation; append raw rows."""
    link = gh_repo.get_github_connection_for_tenant(session, tenant_id)
    if link is None:
        msg = "GitHub is not connected for this tenant"
        raise FetchFatalError(msg)

    run = ing_repo.create_ingestion_run(
        session,
        tenant_id=tenant_id,
        connection_id=link.connection.id,
        connector=CONNECTOR,
        source_trigger=SOURCE_POLL,
    )
    session.commit()

    stats: dict[str, int] = {"records_written": 0}
    executor = FetchExecutor()

    try:
        token = create_github_installation_access_token(settings, link.installation_id)
    except Exception as exc:  # noqa: BLE001
        _logger.exception("installation token failed")
        ing_repo.finish_ingestion_run(
            session,
            run,
            status=ing_repo.RUN_STATUS_FAILED,
            error_summary=f"installation token: {exc}",
            stats=stats,
        )
        session.commit()
        return run

    try:
        _run_with_token(session, link, run, executor, token, stats)
        ing_repo.finish_ingestion_run(
            session,
            run,
            status=ing_repo.RUN_STATUS_SUCCEEDED,
            error_summary=None,
            stats=stats,
        )
    except FetchFatalError as exc:
        _logger.warning("github ingestion fatal: %s", exc)
        ing_repo.finish_ingestion_run(
            session,
            run,
            status=ing_repo.RUN_STATUS_FAILED,
            error_summary=str(exc),
            stats=stats,
        )
    except (FetchTransientError, OSError) as exc:
        _logger.warning("github ingestion transient: %s", exc)
        ing_repo.finish_ingestion_run(
            session,
            run,
            status=ing_repo.RUN_STATUS_PARTIAL,
            error_summary=f"transient: {exc}",
            stats=stats,
        )
    except Exception as exc:  # noqa: BLE001
        _logger.exception("github ingestion failed")
        ing_repo.finish_ingestion_run(
            session,
            run,
            status=ing_repo.RUN_STATUS_FAILED,
            error_summary=str(exc),
            stats=stats,
        )
    finally:
        executor.close()
        session.commit()

    return run


def _run_with_token(
    session: Session,
    link: gh_repo.GithubTenantLink,
    run: IngestionRun,
    executor: FetchExecutor,
    token: str,
    stats: dict[str, int],
) -> None:
    tenant_id = link.tenant_id
    connection_id = link.connection.id
    batch: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal batch
        if batch:
            _flush_batch(session, run, batch, stats)
            batch = []

    repos_meta = _sync_installation_repositories(
        session,
        executor,
        token,
        tenant_id,
        connection_id,
        batch,
        flush,
    )

    for ref in repos_meta:
        try:
            _sync_pulls(
                session,
                executor,
                tenant_id,
                connection_id,
                token,
                ref,
                batch,
                flush,
            )
            _sync_issues(
                session,
                executor,
                tenant_id,
                connection_id,
                token,
                ref,
                batch,
                flush,
            )
            _sync_commits(
                session,
                executor,
                tenant_id,
                connection_id,
                token,
                ref,
                batch,
                flush,
            )
        except GitHubRepoNotFoundError:
            _logger.info("skip missing repo: %s", ref.full_name)
    flush()


def _sync_installation_repositories(
    session: Session,
    executor: FetchExecutor,
    token: str,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    batch: list[dict[str, Any]],
    flush: Callable[[], None],
) -> list[_RepoRef]:
    state = ing_repo.get_sync_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR,
        scope_key=SCOPE_INSTALL_REPOS,
    ) or {}
    page: int = int(state.get("page", 1))
    per_page = 100
    refs: list[_RepoRef] = []

    while True:
        qp: dict[str, Any] = {"per_page": per_page, "page": page}
        resp = _get_json(
            executor,
            "/installation/repositories",
            token,
            params=qp,
        )
        raise_for_github_status(resp)
        data = resp.json()
        if not isinstance(data, dict):
            raise FetchFatalError("installation/repositories: invalid json")
        raw_repos = data.get("repositories") or []
        if not isinstance(raw_repos, list):
            raise FetchFatalError("installation/repositories: repositories not a list")

        for repo in raw_repos:
            if not isinstance(repo, dict):
                continue
            fn = repo.get("full_name")
            if not isinstance(fn, str):
                continue
            nfn = _norm_full_name(fn)
            parts = nfn.split("/", 1)
            if len(parts) != 2 or not parts[0] or not parts[1]:
                continue
            owner, name = parts[0], parts[1]
            dbranch = repo.get("default_branch")
            if not isinstance(dbranch, str):
                dbranch = "main"
            refs.append(
                _RepoRef(
                    full_name=nfn,
                    owner=owner,
                    name=name,
                    default_branch=dbranch,
                    raw=repo,
                ),
            )
            batch.append(
                {
                    "resource_type": RT_REPOSITORY,
                    "external_id": nfn,
                    "api_endpoint": API_INSTALLATION_REpos,
                    "query_params": qp,
                    "payload_body": repo,
                    "http_status": resp.status_code,
                },
            )
            if len(batch) >= 100:
                flush()

        ing_repo.upsert_sync_state(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTOR,
            scope_key=SCOPE_INSTALL_REPOS,
            state={"page": page + 1},
        )
        session.commit()

        if len(raw_repos) < per_page:
            ing_repo.delete_sync_state(
                session,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTOR,
                scope_key=SCOPE_INSTALL_REPOS,
            )
            session.commit()
            break

        page += 1

    return refs


def _sync_pull_commits(
    executor: FetchExecutor,
    token: str,
    ref: _RepoRef,
    pr_number: int,
    list_pulls_query: dict[str, Any],
    batch: list[dict[str, Any]],
    flush: Callable[[], None],
) -> None:
    """Append raw rows linking a PR to each commit on `GET .../pulls/{n}/commits`."""
    page = 1
    per_page = 100
    while True:
        qp: dict[str, Any] = {"per_page": per_page, "page": page}
        path = f"/repos/{ref.owner}/{ref.name}/pulls/{pr_number}/commits"
        resp = _get_json(executor, path, token, params=qp)
        if resp.status_code == 404:
            raise GitHubRepoNotFoundError(ref.full_name)
        raise_for_github_status(resp)
        items = resp.json()
        if not isinstance(items, list):
            raise FetchFatalError("pull commits: expected array")

        for c in items:
            if not isinstance(c, dict):
                continue
            sha = c.get("sha")
            if not isinstance(sha, str) or len(sha) < 7:
                continue
            ext = f"{ref.full_name}#{pr_number}@{sha}"
            batch.append(
                {
                    "resource_type": RT_PULL_REQUEST_COMMIT,
                    "external_id": ext,
                    "api_endpoint": API_LIST_PULL_COMMITS,
                    "query_params": {**qp, "inherited_from": list_pulls_query},
                    "payload_body": c,
                    "http_status": resp.status_code,
                },
            )
            if len(batch) >= 100:
                flush()

        if len(items) < per_page:
            break
        page += 1


def _sync_pulls(
    session: Session,
    executor: FetchExecutor,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    token: str,
    ref: _RepoRef,
    batch: list[dict[str, Any]],
    flush: Callable[[], None],
) -> None:
    scope = _pulls_scope(ref.full_name)
    st = ing_repo.get_sync_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR,
        scope_key=scope,
    ) or {}
    watermark = st.get("watermark")
    watermark_s = watermark if isinstance(watermark, str) and watermark else None

    page = 1
    per_page = 100
    latest_observed: str | None = None

    while True:
        qp: dict[str, Any] = {
            "state": "all",
            "sort": "updated",
            "direction": "desc",
            "per_page": per_page,
            "page": page,
        }
        path = f"/repos/{ref.owner}/{ref.name}/pulls"
        resp = _get_json(executor, path, token, params=qp)
        if resp.status_code == 404:
            raise GitHubRepoNotFoundError(ref.full_name)
        raise_for_github_status(resp)
        items = resp.json()
        if not isinstance(items, list):
            raise FetchFatalError("pulls: expected array")
        if not items:
            break

        if watermark_s is None:
            page_all_old = False
        else:
            page_all_old = all(
                isinstance(pr, dict)
                and isinstance(pr.get("updated_at"), str)
                and pr["updated_at"] <= watermark_s
                for pr in items
            )

        for pr in items:
            if not isinstance(pr, dict):
                continue
            upd = pr.get("updated_at")
            if not isinstance(upd, str):
                continue
            if latest_observed is None or upd > latest_observed:
                latest_observed = upd
            num = pr.get("number")
            if not isinstance(num, int):
                continue
            # First pulls page = most recently updated PRs. Always re-fetch their commit lists
            # so `github.pull_request_commit` rows exist even when the PR body is skipped by
            # the pulls watermark (otherwise `contains` edges are never built after catch-up).
            if page == 1:
                _sync_pull_commits(executor, token, ref, num, qp, batch, flush)
            if watermark_s is not None and upd <= watermark_s:
                continue
            ext = f"{ref.full_name}#{num}"
            batch.append(
                {
                    "resource_type": RT_PULL_REQUEST,
                    "external_id": ext,
                    "api_endpoint": API_LIST_PULLS,
                    "query_params": qp,
                    "payload_body": pr,
                    "http_status": resp.status_code,
                },
            )
            if len(batch) >= 100:
                flush()
            if page != 1:
                _sync_pull_commits(executor, token, ref, num, qp, batch, flush)

        if items and watermark_s is not None and page_all_old:
            break
        if len(items) < per_page:
            break
        page += 1

    new_wm = latest_observed or watermark_s
    if new_wm:
        ing_repo.upsert_sync_state(
            session,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=CONNECTOR,
            scope_key=scope,
            state={"watermark": new_wm},
        )
        session.commit()


def _sync_issues(
    session: Session,
    executor: FetchExecutor,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    token: str,
    ref: _RepoRef,
    batch: list[dict[str, Any]],
    flush: Callable[[], None],
) -> None:
    scope = _issues_scope(ref.full_name)
    st = ing_repo.get_sync_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR,
        scope_key=scope,
    ) or {}
    since = st.get("since")
    since_s = since if isinstance(since, str) else None

    page = 1
    per_page = 100
    path = f"/repos/{ref.owner}/{ref.name}/issues"

    while True:
        qp: dict[str, Any] = {
            "state": "all",
            "per_page": per_page,
            "page": page,
        }
        if since_s:
            qp["since"] = since_s
        resp = _get_json(executor, path, token, params=qp)
        if resp.status_code == 404:
            raise GitHubRepoNotFoundError(ref.full_name)
        raise_for_github_status(resp)
        items = resp.json()
        if not isinstance(items, list):
            raise FetchFatalError("issues: expected array")

        for it in items:
            if not isinstance(it, dict):
                continue
            if it.get("pull_request"):
                continue
            num = it.get("number")
            if not isinstance(num, int):
                continue
            ext = f"{ref.full_name}#{num}"
            batch.append(
                {
                    "resource_type": RT_ISSUE,
                    "external_id": ext,
                    "api_endpoint": API_LIST_ISSUES,
                    "query_params": qp,
                    "payload_body": it,
                    "http_status": resp.status_code,
                },
            )
            if len(batch) >= 100:
                flush()

        if len(items) < per_page:
            break
        page += 1

    since_out = datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ing_repo.upsert_sync_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR,
        scope_key=scope,
        state={"since": since_out},
    )
    session.commit()


def _sync_commits(
    session: Session,
    executor: FetchExecutor,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    token: str,
    ref: _RepoRef,
    batch: list[dict[str, Any]],
    flush: Callable[[], None],
) -> None:
    scope = _commits_scope(ref.full_name)
    st = ing_repo.get_sync_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR,
        scope_key=scope,
    ) or {}
    since = st.get("since")
    since_s = since if isinstance(since, str) else None

    page = 1
    per_page = 100
    path = f"/repos/{ref.owner}/{ref.name}/commits"
    sha = ref.default_branch

    while True:
        qp: dict[str, Any] = {
            "sha": sha,
            "per_page": per_page,
            "page": page,
        }
        if since_s:
            qp["since"] = since_s
        resp = _get_json(executor, path, token, params=qp)
        if resp.status_code == 404:
            raise GitHubRepoNotFoundError(ref.full_name)
        if resp.status_code == 409:
            # GitHub: "Git Repository is empty" on list commits — not an ingestion failure.
            _logger.info(
                "skip commits for repo %s (github 409 empty or conflict): %s",
                ref.full_name,
                (resp.text or "")[:200].replace("\n", " "),
            )
            since_out = datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace(
                "+00:00",
                "Z",
            )
            ing_repo.upsert_sync_state(
                session,
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector=CONNECTOR,
                scope_key=scope,
                state={"since": since_out},
            )
            session.commit()
            return
        raise_for_github_status(resp)
        items = resp.json()
        if not isinstance(items, list):
            raise FetchFatalError("commits: expected array")

        for c in items:
            if not isinstance(c, dict):
                continue
            h = c.get("sha")
            if not isinstance(h, str):
                continue
            ext = f"{ref.full_name}@{h}"
            batch.append(
                {
                    "resource_type": RT_COMMIT,
                    "external_id": ext,
                    "api_endpoint": API_LIST_COMMITS,
                    "query_params": qp,
                    "payload_body": c,
                    "http_status": resp.status_code,
                },
            )
            if len(batch) >= 100:
                flush()

        if len(items) < per_page:
            break
        page += 1

    since_out = datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ing_repo.upsert_sync_state(
        session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR,
        scope_key=scope,
        state={"since": since_out},
    )
    session.commit()
