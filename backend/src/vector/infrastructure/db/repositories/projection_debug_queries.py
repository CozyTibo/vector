"""Read-only queries for projection debug UI."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.github_projection import (
    GithubCommit,
    GithubIssue,
    GithubPullRequest,
    GithubRepository,
    GithubUser,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant_connection import TenantConnection


@dataclass(frozen=True)
class RowsPage:
    total: int
    items: Sequence[Any]


def connection_belongs_to_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> bool:
    stmt = select(TenantConnection.id).where(
        TenantConnection.id == connection_id,
        TenantConnection.tenant_id == tenant_id,
    )
    return session.scalar(stmt) is not None


def get_raw_record_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    record_id: int,
) -> RawIngestionRecord | None:
    stmt = select(RawIngestionRecord).where(
        RawIngestionRecord.id == record_id,
        RawIngestionRecord.tenant_id == tenant_id,
    )
    return session.scalar(stmt)


def _ilike_q(q: str | None, *cols: Any) -> Any | None:
    if not q or not q.strip():
        return None
    pat = f"%{q.strip()}%"
    return or_(*[c.ilike(pat) for c in cols])


def list_github_repositories(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    limit: int,
    offset: int,
    q: str | None,
) -> RowsPage:
    filters = [
        GithubRepository.tenant_id == tenant_id,
        GithubRepository.connection_id == connection_id,
    ]
    extra = _ilike_q(
        q,
        GithubRepository.full_name,
        GithubRepository.name,
        func.cast(GithubRepository.repository_github_id, String),
    )
    if extra is not None:
        filters.append(extra)
    cnt_stmt = select(func.count()).select_from(GithubRepository).where(*filters)
    total = int(session.scalar(cnt_stmt) or 0)
    stmt = (
        select(GithubRepository)
        .where(*filters)
        .order_by(GithubRepository.full_name.asc().nulls_last())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.scalars(stmt).all())
    return RowsPage(total=total, items=items)


def list_github_pull_requests(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    limit: int,
    offset: int,
    q: str | None,
) -> RowsPage:
    filters = [
        GithubPullRequest.tenant_id == tenant_id,
        GithubPullRequest.connection_id == connection_id,
    ]
    extra = _ilike_q(
        q,
        GithubPullRequest.title,
        GithubPullRequest.repo_full_name,
        func.cast(GithubPullRequest.pr_number, String),
        func.cast(GithubPullRequest.repository_github_id, String),
    )
    if extra is not None:
        filters.append(extra)
    cnt_stmt = select(func.count()).select_from(GithubPullRequest).where(*filters)
    total = int(session.scalar(cnt_stmt) or 0)
    stmt = (
        select(GithubPullRequest)
        .where(*filters)
        .order_by(
            GithubPullRequest.repo_full_name.asc().nulls_last(),
            GithubPullRequest.pr_number.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    items = list(session.scalars(stmt).all())
    return RowsPage(total=total, items=items)


def list_github_issues(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    limit: int,
    offset: int,
    q: str | None,
) -> RowsPage:
    filters = [
        GithubIssue.tenant_id == tenant_id,
        GithubIssue.connection_id == connection_id,
    ]
    extra = _ilike_q(
        q,
        GithubIssue.title,
        GithubIssue.repo_full_name,
        func.cast(GithubIssue.issue_number, String),
        func.cast(GithubIssue.repository_github_id, String),
    )
    if extra is not None:
        filters.append(extra)
    cnt_stmt = select(func.count()).select_from(GithubIssue).where(*filters)
    total = int(session.scalar(cnt_stmt) or 0)
    stmt = (
        select(GithubIssue)
        .where(*filters)
        .order_by(
            GithubIssue.repo_full_name.asc().nulls_last(),
            GithubIssue.issue_number.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    items = list(session.scalars(stmt).all())
    return RowsPage(total=total, items=items)


def list_github_commits(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    limit: int,
    offset: int,
    q: str | None,
) -> RowsPage:
    filters = [
        GithubCommit.tenant_id == tenant_id,
        GithubCommit.connection_id == connection_id,
    ]
    extra = _ilike_q(
        q,
        GithubCommit.repo_full_name,
        GithubCommit.commit_sha,
        GithubCommit.message,
        func.cast(GithubCommit.repository_github_id, String),
    )
    if extra is not None:
        filters.append(extra)
    cnt_stmt = select(func.count()).select_from(GithubCommit).where(*filters)
    total = int(session.scalar(cnt_stmt) or 0)
    stmt = (
        select(GithubCommit)
        .where(*filters)
        .order_by(GithubCommit.commit_sha.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.scalars(stmt).all())
    return RowsPage(total=total, items=items)


def list_github_users(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    limit: int,
    offset: int,
    q: str | None,
) -> RowsPage:
    filters = [
        GithubUser.tenant_id == tenant_id,
        GithubUser.connection_id == connection_id,
    ]
    extra = _ilike_q(
        q,
        GithubUser.login,
        func.cast(GithubUser.github_id, String),
    )
    if extra is not None:
        filters.append(extra)
    cnt_stmt = select(func.count()).select_from(GithubUser).where(*filters)
    total = int(session.scalar(cnt_stmt) or 0)
    stmt = (
        select(GithubUser)
        .where(*filters)
        .order_by(GithubUser.login.asc().nulls_last())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.scalars(stmt).all())
    return RowsPage(total=total, items=items)


def last_raw_fetched_at_for_connection(
    session: Session,
    connection_id: uuid.UUID,
) -> datetime | None:
    stmt = select(func.max(RawIngestionRecord.fetched_at)).where(
        RawIngestionRecord.connection_id == connection_id,
    )
    return session.scalar(stmt)


def list_tenant_connections_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> list[TenantConnection]:
    stmt = (
        select(TenantConnection)
        .where(TenantConnection.tenant_id == tenant_id)
        .order_by(TenantConnection.created_at.asc())
    )
    return list(session.scalars(stmt).all())


def list_raw_ingestion_records_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
) -> RowsPage:
    filters = [RawIngestionRecord.tenant_id == tenant_id]
    cnt_stmt = select(func.count()).select_from(RawIngestionRecord).where(*filters)
    total = int(session.scalar(cnt_stmt) or 0)
    stmt = (
        select(RawIngestionRecord)
        .where(*filters)
        .order_by(RawIngestionRecord.replay_sequence.desc(), RawIngestionRecord.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.scalars(stmt).all())
    return RowsPage(total=total, items=items)
