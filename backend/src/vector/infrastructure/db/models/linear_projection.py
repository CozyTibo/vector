"""Linear Step 2 projection tables (current observed state)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class LinearUser(Base):
    __tablename__ = "linear_users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    linear_user_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    guest: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    admin: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_raw_record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_replay_sequence: Mapped[int] = mapped_column(Integer, nullable=False)


class LinearTeam(Base):
    __tablename__ = "linear_teams"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    linear_team_id: Mapped[str] = mapped_column(Text, primary_key=True)
    key: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    private: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_raw_record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_replay_sequence: Mapped[int] = mapped_column(Integer, nullable=False)


class LinearProject(Base):
    __tablename__ = "linear_projects"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    linear_project_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_raw_record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_replay_sequence: Mapped[int] = mapped_column(Integer, nullable=False)


class LinearIssue(Base):
    __tablename__ = "linear_issues"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    linear_issue_id: Mapped[str] = mapped_column(Text, primary_key=True)
    identifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    state_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    creator_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_issue_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    cycle_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    labels_json: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_raw_record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_replay_sequence: Mapped[int] = mapped_column(Integer, nullable=False)


class LinearIssueComment(Base):
    __tablename__ = "linear_issue_comments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    linear_comment_id: Mapped[str] = mapped_column(Text, primary_key=True)
    linear_issue_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    issue_identifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_raw_record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_replay_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
