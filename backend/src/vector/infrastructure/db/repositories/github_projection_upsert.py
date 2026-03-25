"""UPSERT helpers for GitHub projection tables (COALESCE + GREATEST merge rules)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.github_projection import (
    GithubCommit,
    GithubIssue,
    GithubPullRequest,
    GithubRepository,
    GithubUser,
)


def _coalesce_new(excluded_col: Any, table_col: Any) -> Any:
    return func.coalesce(excluded_col, table_col)


def _greatest_ts(excluded_col: Any, table_col: Any) -> Any:
    return case(
        (excluded_col.is_(None), table_col),
        else_=func.greatest(func.coalesce(table_col, excluded_col), excluded_col),
    )


def upsert_github_repository(
    session: Session,
    *,
    values: dict[str, Any],
) -> None:
    t = GithubRepository.__table__
    ins = pg_insert(GithubRepository).values(**values)
    ex = ins.excluded
    stmt = ins.on_conflict_do_update(
        index_elements=[t.c.connection_id, t.c.repository_github_id],
        set_={
            "tenant_id": ex.tenant_id,
            "node_id": _coalesce_new(ex.node_id, t.c.node_id),
            "name": _coalesce_new(ex.name, t.c.name),
            "full_name": _coalesce_new(ex.full_name, t.c.full_name),
            "owner_login": _coalesce_new(ex.owner_login, t.c.owner_login),
            "owner_github_id": _coalesce_new(ex.owner_github_id, t.c.owner_github_id),
            "private": _coalesce_new(ex.private, t.c.private),
            "description": _coalesce_new(ex.description, t.c.description),
            "default_branch": _coalesce_new(ex.default_branch, t.c.default_branch),
            "html_url": _coalesce_new(ex.html_url, t.c.html_url),
            "archived": _coalesce_new(ex.archived, t.c.archived),
            "disabled": _coalesce_new(ex.disabled, t.c.disabled),
            "fork": _coalesce_new(ex.fork, t.c.fork),
            "pushed_at": _greatest_ts(ex.pushed_at, t.c.pushed_at),
            "github_created_at": _greatest_ts(ex.github_created_at, t.c.github_created_at),
            "github_updated_at": _greatest_ts(ex.github_updated_at, t.c.github_updated_at),
            "last_raw_record_id": ex.last_raw_record_id,
            "last_observed_at": ex.last_observed_at,
            "last_replay_sequence": ex.last_replay_sequence,
        },
    )
    session.execute(stmt)


def upsert_github_pull_request(session: Session, *, values: dict[str, Any]) -> None:
    t = GithubPullRequest.__table__
    ins = pg_insert(GithubPullRequest).values(**values)
    ex = ins.excluded
    stmt = ins.on_conflict_do_update(
        index_elements=[t.c.connection_id, t.c.repository_github_id, t.c.pr_number],
        set_={
            "tenant_id": ex.tenant_id,
            "pull_request_github_id": _coalesce_new(
                ex.pull_request_github_id,
                t.c.pull_request_github_id,
            ),
            "node_id": _coalesce_new(ex.node_id, t.c.node_id),
            "repo_full_name": _coalesce_new(ex.repo_full_name, t.c.repo_full_name),
            "title": _coalesce_new(ex.title, t.c.title),
            "body": _coalesce_new(ex.body, t.c.body),
            "state": _coalesce_new(ex.state, t.c.state),
            "draft": _coalesce_new(ex.draft, t.c.draft),
            "author_github_id": _coalesce_new(ex.author_github_id, t.c.author_github_id),
            "author_login": _coalesce_new(ex.author_login, t.c.author_login),
            "head_sha": _coalesce_new(ex.head_sha, t.c.head_sha),
            "head_ref": _coalesce_new(ex.head_ref, t.c.head_ref),
            "base_sha": _coalesce_new(ex.base_sha, t.c.base_sha),
            "base_ref": _coalesce_new(ex.base_ref, t.c.base_ref),
            "html_url": _coalesce_new(ex.html_url, t.c.html_url),
            "merged_at": _greatest_ts(ex.merged_at, t.c.merged_at),
            "closed_at": _greatest_ts(ex.closed_at, t.c.closed_at),
            "github_created_at": _greatest_ts(ex.github_created_at, t.c.github_created_at),
            "github_updated_at": _greatest_ts(ex.github_updated_at, t.c.github_updated_at),
            "last_raw_record_id": ex.last_raw_record_id,
            "last_observed_at": ex.last_observed_at,
            "last_replay_sequence": ex.last_replay_sequence,
        },
    )
    session.execute(stmt)


def upsert_github_issue(session: Session, *, values: dict[str, Any]) -> None:
    t = GithubIssue.__table__
    ins = pg_insert(GithubIssue).values(**values)
    ex = ins.excluded
    stmt = ins.on_conflict_do_update(
        index_elements=[t.c.connection_id, t.c.repository_github_id, t.c.issue_number],
        set_={
            "tenant_id": ex.tenant_id,
            "issue_github_id": _coalesce_new(ex.issue_github_id, t.c.issue_github_id),
            "node_id": _coalesce_new(ex.node_id, t.c.node_id),
            "repo_full_name": _coalesce_new(ex.repo_full_name, t.c.repo_full_name),
            "title": _coalesce_new(ex.title, t.c.title),
            "body": _coalesce_new(ex.body, t.c.body),
            "state": _coalesce_new(ex.state, t.c.state),
            "author_github_id": _coalesce_new(ex.author_github_id, t.c.author_github_id),
            "author_login": _coalesce_new(ex.author_login, t.c.author_login),
            "html_url": _coalesce_new(ex.html_url, t.c.html_url),
            "locked": _coalesce_new(ex.locked, t.c.locked),
            "github_created_at": _greatest_ts(ex.github_created_at, t.c.github_created_at),
            "github_updated_at": _greatest_ts(ex.github_updated_at, t.c.github_updated_at),
            "closed_at": _greatest_ts(ex.closed_at, t.c.closed_at),
            "last_raw_record_id": ex.last_raw_record_id,
            "last_observed_at": ex.last_observed_at,
            "last_replay_sequence": ex.last_replay_sequence,
        },
    )
    session.execute(stmt)


def upsert_github_commit(session: Session, *, values: dict[str, Any]) -> None:
    t = GithubCommit.__table__
    ins = pg_insert(GithubCommit).values(**values)
    ex = ins.excluded
    stmt = ins.on_conflict_do_update(
        index_elements=[t.c.connection_id, t.c.repository_github_id, t.c.commit_sha],
        set_={
            "tenant_id": ex.tenant_id,
            "message": _coalesce_new(ex.message, t.c.message),
            "author_name": _coalesce_new(ex.author_name, t.c.author_name),
            "author_email": _coalesce_new(ex.author_email, t.c.author_email),
            "author_date": _greatest_ts(ex.author_date, t.c.author_date),
            "committer_name": _coalesce_new(ex.committer_name, t.c.committer_name),
            "committer_email": _coalesce_new(ex.committer_email, t.c.committer_email),
            "committer_date": _greatest_ts(ex.committer_date, t.c.committer_date),
            "author_github_id": _coalesce_new(ex.author_github_id, t.c.author_github_id),
            "committer_github_id": _coalesce_new(ex.committer_github_id, t.c.committer_github_id),
            "html_url": _coalesce_new(ex.html_url, t.c.html_url),
            "parents_json": _coalesce_new(ex.parents_json, t.c.parents_json),
            "last_raw_record_id": ex.last_raw_record_id,
            "last_observed_at": ex.last_observed_at,
            "last_replay_sequence": ex.last_replay_sequence,
        },
    )
    session.execute(stmt)


def upsert_github_user(session: Session, *, values: dict[str, Any]) -> None:
    t = GithubUser.__table__
    ins = pg_insert(GithubUser).values(**values)
    ex = ins.excluded
    stmt = ins.on_conflict_do_update(
        index_elements=[t.c.connection_id, t.c.github_id],
        set_={
            "tenant_id": ex.tenant_id,
            "login": _coalesce_new(ex.login, t.c.login),
            "type": _coalesce_new(ex.type, t.c.type),
            "avatar_url": _coalesce_new(ex.avatar_url, t.c.avatar_url),
            "html_url": _coalesce_new(ex.html_url, t.c.html_url),
            "name": _coalesce_new(ex.name, t.c.name),
            "bio": _coalesce_new(ex.bio, t.c.bio),
            "site_admin": _coalesce_new(ex.site_admin, t.c.site_admin),
            "last_raw_record_id": ex.last_raw_record_id,
            "last_observed_at": ex.last_observed_at,
            "last_replay_sequence": ex.last_replay_sequence,
        },
    )
    session.execute(stmt)
