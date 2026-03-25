"""Map raw_ingestion_records (GitHub) → projection UPSERTs."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.projections.github.datetime_parse import parse_github_datetime
from vector.domains.projections.github.external_id import (
    parse_commit_external_id,
    parse_issue_or_pr_external_id,
)
from vector.domains.projections.github.metrics import GithubProjectionMetrics
from vector.domains.projections.github.resource_types import (
    RT_COMMIT,
    RT_ISSUE,
    RT_PULL_REQUEST,
    RT_REPOSITORY,
)
from vector.infrastructure.db.models.github_projection import GithubRepository
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.repositories import github_projection_upsert as gh_upsert

_logger = logging.getLogger(__name__)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _as_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _user_blob(user: Any) -> dict[str, Any] | None:
    return user if isinstance(user, dict) else None


def _repo_lookup_github_id(
    session: Session,
    connection_id: Any,
    full_name: str,
) -> int | None:
    fn = full_name.strip().lower()
    q = select(GithubRepository.repository_github_id).where(
        GithubRepository.connection_id == connection_id,
        func.lower(GithubRepository.full_name) == fn,
    )
    return session.scalar(q)


def _maybe_upsert_user(
    session: Session,
    *,
    tenant_id: Any,
    connection_id: Any,
    user: dict[str, Any] | None,
    last_raw_record_id: int,
    last_observed_at: Any,
    last_replay_sequence: int,
) -> None:
    if not user:
        return
    uid = _as_int(user.get("id"))
    if uid is None:
        return
    gh_upsert.upsert_github_user(
        session,
        values={
            "tenant_id": tenant_id,
            "connection_id": connection_id,
            "github_id": uid,
            "login": _as_str(user.get("login")),
            "type": _as_str(user.get("type")),
            "avatar_url": _as_str(user.get("avatar_url")),
            "html_url": _as_str(user.get("html_url")),
            "name": _as_str(user.get("name")),
            "bio": _as_str(user.get("bio")),
            "site_admin": _as_bool(user.get("site_admin")),
            "last_raw_record_id": last_raw_record_id,
            "last_observed_at": last_observed_at,
            "last_replay_sequence": last_replay_sequence,
        },
    )


def handle_github_raw_row(
    session: Session,
    raw: RawIngestionRecord,
    metrics: GithubProjectionMetrics,
) -> None:
    if raw.connector != "github":
        return
    if not (200 <= raw.http_status <= 299):
        return

    prov = {
        "last_raw_record_id": raw.id,
        "last_observed_at": raw.fetched_at,
        "last_replay_sequence": raw.replay_sequence,
    }
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}

    rtype = raw.resource_type
    if rtype == RT_REPOSITORY:
        _project_repository(session, raw, payload, prov)
    elif rtype == RT_PULL_REQUEST:
        _project_pull_request(session, raw, payload, prov)
    elif rtype == RT_ISSUE:
        _project_issue(session, raw, payload, prov, metrics)
    elif rtype == RT_COMMIT:
        _project_commit(session, raw, payload, prov, metrics)


def _project_repository(
    session: Session,
    raw: RawIngestionRecord,
    payload: dict[str, Any],
    prov: dict[str, Any],
) -> None:
    rid = _as_int(payload.get("id"))
    if rid is None:
        return
    owner = _user_blob(payload.get("owner"))
    _maybe_upsert_user(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        user=owner,
        **prov,
    )
    gh_upsert.upsert_github_repository(
        session,
        values={
            "tenant_id": raw.tenant_id,
            "connection_id": raw.connection_id,
            "repository_github_id": rid,
            "node_id": _as_str(payload.get("node_id")),
            "name": _as_str(payload.get("name")),
            "full_name": _as_str(payload.get("full_name")),
            "owner_login": _as_str(owner.get("login")) if owner else None,
            "owner_github_id": _as_int(owner.get("id")) if owner else None,
            "private": _as_bool(payload.get("private")),
            "description": _as_str(payload.get("description")),
            "default_branch": _as_str(payload.get("default_branch")),
            "html_url": _as_str(payload.get("html_url")),
            "archived": _as_bool(payload.get("archived")),
            "disabled": _as_bool(payload.get("disabled")),
            "fork": _as_bool(payload.get("fork")),
            "pushed_at": parse_github_datetime(payload.get("pushed_at")),
            "github_created_at": parse_github_datetime(payload.get("created_at")),
            "github_updated_at": parse_github_datetime(payload.get("updated_at")),
            **prov,
        },
    )


def _project_pull_request(
    session: Session,
    raw: RawIngestionRecord,
    payload: dict[str, Any],
    prov: dict[str, Any],
) -> None:
    user = _user_blob(payload.get("user"))
    _maybe_upsert_user(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        user=user,
        **prov,
    )
    base = payload.get("base")
    base_repo = base.get("repo") if isinstance(base, dict) else None
    repo_github_id = _as_int(base_repo.get("id")) if isinstance(base_repo, dict) else None
    repo_full_name = _as_str(base_repo.get("full_name")) if isinstance(base_repo, dict) else None
    if repo_github_id is None:
        parsed = parse_issue_or_pr_external_id(raw.external_id)
        if parsed is None:
            return
        fn, _num = parsed
        repo_github_id = _repo_lookup_github_id(session, raw.connection_id, fn)
    if repo_github_id is None:
        return
    num = _as_int(payload.get("number"))
    if num is None:
        return
    head = payload.get("head")
    base_d = base if isinstance(base, dict) else None
    head_d = head if isinstance(head, dict) else None
    gh_upsert.upsert_github_pull_request(
        session,
        values={
            "tenant_id": raw.tenant_id,
            "connection_id": raw.connection_id,
            "repository_github_id": repo_github_id,
            "pr_number": num,
            "pull_request_github_id": _as_int(payload.get("id")),
            "node_id": _as_str(payload.get("node_id")),
            "repo_full_name": repo_full_name,
            "title": _as_str(payload.get("title")),
            "body": _as_str(payload.get("body")),
            "state": _as_str(payload.get("state")),
            "draft": _as_bool(payload.get("draft")),
            "author_github_id": _as_int(user.get("id")) if user else None,
            "author_login": _as_str(user.get("login")) if user else None,
            "head_sha": _as_str(head_d.get("sha")) if head_d else None,
            "head_ref": _as_str(head_d.get("ref")) if head_d else None,
            "base_sha": _as_str(base_d.get("sha")) if base_d else None,
            "base_ref": _as_str(base_d.get("ref")) if base_d else None,
            "html_url": _as_str(payload.get("html_url")),
            "merged_at": parse_github_datetime(payload.get("merged_at")),
            "closed_at": parse_github_datetime(payload.get("closed_at")),
            "github_created_at": parse_github_datetime(payload.get("created_at")),
            "github_updated_at": parse_github_datetime(payload.get("updated_at")),
            **prov,
        },
    )


def _project_issue(
    session: Session,
    raw: RawIngestionRecord,
    payload: dict[str, Any],
    prov: dict[str, Any],
    _metrics: GithubProjectionMetrics,
) -> None:
    if isinstance(payload.get("pull_request"), dict):
        return
    user = _user_blob(payload.get("user"))
    _maybe_upsert_user(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        user=user,
        **prov,
    )
    repo_obj = payload.get("repository")
    repo_github_id = _as_int(repo_obj.get("id")) if isinstance(repo_obj, dict) else None
    repo_full_name = _as_str(repo_obj.get("full_name")) if isinstance(repo_obj, dict) else None
    if repo_github_id is None:
        parsed = parse_issue_or_pr_external_id(raw.external_id)
        if parsed is None:
            return
        fn, _num = parsed
        repo_github_id = _repo_lookup_github_id(session, raw.connection_id, fn)
    if repo_github_id is None:
        return
    num = _as_int(payload.get("number"))
    if num is None:
        return
    gh_upsert.upsert_github_issue(
        session,
        values={
            "tenant_id": raw.tenant_id,
            "connection_id": raw.connection_id,
            "repository_github_id": repo_github_id,
            "issue_number": num,
            "issue_github_id": _as_int(payload.get("id")),
            "node_id": _as_str(payload.get("node_id")),
            "repo_full_name": repo_full_name,
            "title": _as_str(payload.get("title")),
            "body": _as_str(payload.get("body")),
            "state": _as_str(payload.get("state")),
            "author_github_id": _as_int(user.get("id")) if user else None,
            "author_login": _as_str(user.get("login")) if user else None,
            "html_url": _as_str(payload.get("html_url")),
            "locked": _as_bool(payload.get("locked")),
            "github_created_at": parse_github_datetime(payload.get("created_at")),
            "github_updated_at": parse_github_datetime(payload.get("updated_at")),
            "closed_at": parse_github_datetime(payload.get("closed_at")),
            **prov,
        },
    )


def _parents_shas(payload: dict[str, Any]) -> list[str] | None:
    parents = payload.get("parents")
    if not isinstance(parents, list):
        return None
    out: list[str] = []
    for p in parents:
        if isinstance(p, dict):
            sha = _as_str(p.get("sha"))
            if sha:
                out.append(sha)
    return out or None


def _project_commit(
    session: Session,
    raw: RawIngestionRecord,
    payload: dict[str, Any],
    prov: dict[str, Any],
    metrics: GithubProjectionMetrics,
) -> None:
    parsed = parse_commit_external_id(raw.external_id)
    if parsed is None:
        return
    full_name, sha = parsed
    rid = _repo_lookup_github_id(session, raw.connection_id, full_name)
    if rid is None:
        metrics.commits_skipped_missing_repo += 1
        _logger.debug("commit projection skipped (no repo yet): %s", raw.external_id)
        return

    author_u = _user_blob(payload.get("author"))
    committer_u = _user_blob(payload.get("committer"))
    _maybe_upsert_user(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        user=author_u,
        **prov,
    )
    _maybe_upsert_user(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        user=committer_u,
        **prov,
    )

    inner = payload.get("commit")
    inner_d = inner if isinstance(inner, dict) else None
    auth = inner_d.get("author") if inner_d else None
    cmtr = inner_d.get("committer") if inner_d else None
    auth_d = auth if isinstance(auth, dict) else None
    cmtr_d = cmtr if isinstance(cmtr, dict) else None

    parents_json = _parents_shas(payload)

    gh_upsert.upsert_github_commit(
        session,
        values={
            "tenant_id": raw.tenant_id,
            "connection_id": raw.connection_id,
            "repository_github_id": rid,
            "commit_sha": sha,
            "repo_full_name": full_name,
            "message": _as_str(inner_d.get("message")) if inner_d else None,
            "author_name": _as_str(auth_d.get("name")) if auth_d else None,
            "author_email": _as_str(auth_d.get("email")) if auth_d else None,
            "author_date": parse_github_datetime(auth_d.get("date")) if auth_d else None,
            "committer_name": _as_str(cmtr_d.get("name")) if cmtr_d else None,
            "committer_email": _as_str(cmtr_d.get("email")) if cmtr_d else None,
            "committer_date": parse_github_datetime(cmtr_d.get("date")) if cmtr_d else None,
            "author_github_id": _as_int(author_u.get("id")) if author_u else None,
            "committer_github_id": _as_int(committer_u.get("id")) if committer_u else None,
            "html_url": _as_str(payload.get("html_url")),
            "parents_json": parents_json,
            **prov,
        },
    )


