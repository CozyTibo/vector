"""GitHub Step 2 projection tables (current observed state)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class GithubRepository(Base):
    __tablename__ = "github_repositories"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    repository_github_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    node_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_login: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_github_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    private: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    disabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fork: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    github_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    github_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_raw_record_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_replay_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)


class GithubPullRequest(Base):
    __tablename__ = "github_pull_requests"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    repository_github_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pr_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    pull_request_github_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    node_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    repo_full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    author_github_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    author_login: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_sha: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_sha: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    github_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    github_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_raw_record_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_replay_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)


class GithubIssue(Base):
    __tablename__ = "github_issues"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    repository_github_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    issue_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_github_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    node_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    repo_full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_github_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    author_login: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    github_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    github_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_raw_record_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_replay_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)


class GithubCommit(Base):
    __tablename__ = "github_commits"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    repository_github_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    commit_sha: Mapped[str] = mapped_column(Text, primary_key=True)
    repo_full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    committer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    committer_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    committer_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    author_github_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    committer_github_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    html_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    parents_json: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    last_raw_record_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_replay_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)


class GithubUser(Base):
    __tablename__ = "github_users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    github_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    login: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    site_admin: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_raw_record_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_replay_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
