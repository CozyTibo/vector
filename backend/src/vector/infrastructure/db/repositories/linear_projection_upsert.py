"""UPSERT helpers for Linear projection tables."""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.linear_projection import (
    LinearIssue,
    LinearIssueComment,
    LinearProject,
    LinearTeam,
    LinearUser,
)


def _coalesce_new(excluded_col: Any, table_col: Any) -> Any:
    return func.coalesce(excluded_col, table_col)


def _greatest_ts(excluded_col: Any, table_col: Any) -> Any:
    return case(
        (excluded_col.is_(None), table_col),
        else_=func.greatest(func.coalesce(table_col, excluded_col), excluded_col),
    )


def upsert_linear_user(session: Session, *, values: dict[str, Any]) -> None:
    t = LinearUser.__table__
    ins = pg_insert(LinearUser).values(**values)
    ex = ins.excluded
    stmt = ins.on_conflict_do_update(
        index_elements=[t.c.connection_id, t.c.linear_user_id],
        set_={
            "tenant_id": ex.tenant_id,
            "name": _coalesce_new(ex.name, t.c.name),
            "display_name": _coalesce_new(ex.display_name, t.c.display_name),
            "email": _coalesce_new(ex.email, t.c.email),
            "avatar_url": _coalesce_new(ex.avatar_url, t.c.avatar_url),
            "active": _coalesce_new(ex.active, t.c.active),
            "guest": _coalesce_new(ex.guest, t.c.guest),
            "admin": _coalesce_new(ex.admin, t.c.admin),
            "last_raw_record_id": ex.last_raw_record_id,
            "last_observed_at": ex.last_observed_at,
            "last_replay_sequence": ex.last_replay_sequence,
        },
    )
    session.execute(stmt)


def upsert_linear_team(session: Session, *, values: dict[str, Any]) -> None:
    t = LinearTeam.__table__
    ins = pg_insert(LinearTeam).values(**values)
    ex = ins.excluded
    stmt = ins.on_conflict_do_update(
        index_elements=[t.c.connection_id, t.c.linear_team_id],
        set_={
            "tenant_id": ex.tenant_id,
            "key": _coalesce_new(ex.key, t.c.key),
            "name": _coalesce_new(ex.name, t.c.name),
            "description": _coalesce_new(ex.description, t.c.description),
            "private": _coalesce_new(ex.private, t.c.private),
            "last_raw_record_id": ex.last_raw_record_id,
            "last_observed_at": ex.last_observed_at,
            "last_replay_sequence": ex.last_replay_sequence,
        },
    )
    session.execute(stmt)


def upsert_linear_project(session: Session, *, values: dict[str, Any]) -> None:
    t = LinearProject.__table__
    ins = pg_insert(LinearProject).values(**values)
    ex = ins.excluded
    stmt = ins.on_conflict_do_update(
        index_elements=[t.c.connection_id, t.c.linear_project_id],
        set_={
            "tenant_id": ex.tenant_id,
            "name": _coalesce_new(ex.name, t.c.name),
            "slug": _coalesce_new(ex.slug, t.c.slug),
            "description": _coalesce_new(ex.description, t.c.description),
            "state": _coalesce_new(ex.state, t.c.state),
            "last_raw_record_id": ex.last_raw_record_id,
            "last_observed_at": ex.last_observed_at,
            "last_replay_sequence": ex.last_replay_sequence,
        },
    )
    session.execute(stmt)


def upsert_linear_issue(session: Session, *, values: dict[str, Any]) -> None:
    t = LinearIssue.__table__
    ins = pg_insert(LinearIssue).values(**values)
    ex = ins.excluded
    stmt = ins.on_conflict_do_update(
        index_elements=[t.c.connection_id, t.c.linear_issue_id],
        set_={
            "tenant_id": ex.tenant_id,
            "identifier": _coalesce_new(ex.identifier, t.c.identifier),
            "title": _coalesce_new(ex.title, t.c.title),
            "description": _coalesce_new(ex.description, t.c.description),
            "priority": _coalesce_new(ex.priority, t.c.priority),
            "estimate": _coalesce_new(ex.estimate, t.c.estimate),
            "state_id": _coalesce_new(ex.state_id, t.c.state_id),
            "state_name": _coalesce_new(ex.state_name, t.c.state_name),
            "state_type": _coalesce_new(ex.state_type, t.c.state_type),
            "team_id": _coalesce_new(ex.team_id, t.c.team_id),
            "assignee_id": _coalesce_new(ex.assignee_id, t.c.assignee_id),
            "creator_id": _coalesce_new(ex.creator_id, t.c.creator_id),
            "project_id": _coalesce_new(ex.project_id, t.c.project_id),
            "parent_issue_id": _coalesce_new(ex.parent_issue_id, t.c.parent_issue_id),
            "cycle_id": _coalesce_new(ex.cycle_id, t.c.cycle_id),
            "labels_json": _coalesce_new(ex.labels_json, t.c.labels_json),
            "created_at": _greatest_ts(ex.created_at, t.c.created_at),
            "updated_at": _greatest_ts(ex.updated_at, t.c.updated_at),
            "archived_at": _coalesce_new(ex.archived_at, t.c.archived_at),
            "last_raw_record_id": ex.last_raw_record_id,
            "last_observed_at": ex.last_observed_at,
            "last_replay_sequence": ex.last_replay_sequence,
        },
    )
    session.execute(stmt)


def upsert_linear_issue_comment(session: Session, *, values: dict[str, Any]) -> None:
    t = LinearIssueComment.__table__
    ins = pg_insert(LinearIssueComment).values(**values)
    ex = ins.excluded
    stmt = ins.on_conflict_do_update(
        index_elements=[t.c.connection_id, t.c.linear_comment_id],
        set_={
            "tenant_id": ex.tenant_id,
            "linear_issue_id": _coalesce_new(ex.linear_issue_id, t.c.linear_issue_id),
            "issue_identifier": _coalesce_new(ex.issue_identifier, t.c.issue_identifier),
            "body": _coalesce_new(ex.body, t.c.body),
            "user_id": _coalesce_new(ex.user_id, t.c.user_id),
            "created_at": _greatest_ts(ex.created_at, t.c.created_at),
            "updated_at": _greatest_ts(ex.updated_at, t.c.updated_at),
            "last_raw_record_id": ex.last_raw_record_id,
            "last_observed_at": ex.last_observed_at,
            "last_replay_sequence": ex.last_replay_sequence,
        },
    )
    session.execute(stmt)
