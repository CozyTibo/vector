"""Map raw_ingestion_records (Linear) → projection UPSERTs."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.projections.linear.datetime_parse import parse_linear_datetime
from vector.domains.projections.linear.resource_types import (
    RT_COMMENT,
    RT_CYCLE,
    RT_INITIATIVE,
    RT_ISSUE,
    RT_ISSUE_LABEL,
    RT_ISSUE_RELATION,
    RT_PROJECT,
    RT_TEAM,
    RT_USER,
    RT_VIEWER,
    RT_WORKFLOW_STATE,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.repositories import linear_projection_upsert as ln_upsert

_logger = logging.getLogger(__name__)


def _as_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _user_blob(user: Any) -> dict[str, Any] | None:
    return user if isinstance(user, dict) else None


def _labels_blob(issue: dict[str, Any]) -> list[dict[str, Any]] | None:
    labels = issue.get("labels")
    if not isinstance(labels, dict):
        return None
    nodes = labels.get("nodes")
    if not isinstance(nodes, list):
        return None
    out: list[dict[str, Any]] = []
    for n in nodes:
        if isinstance(n, dict):
            out.append(
                {
                    "id": n.get("id"),
                    "name": n.get("name"),
                    "color": n.get("color"),
                },
            )
    return out or None


def handle_linear_raw_row(session: Session, raw: RawIngestionRecord) -> None:
    if raw.connector != "linear":
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

    if rtype == RT_VIEWER:
        _project_viewer(session, raw, payload, prov)
    elif rtype == RT_USER:
        _project_user_node(session, raw, payload, prov)
    elif rtype == RT_TEAM:
        _project_team(session, raw, payload, prov)
    elif rtype == RT_PROJECT:
        _project_project(session, raw, payload, prov)
    elif rtype == RT_ISSUE:
        _project_issue(session, raw, payload, prov)
    elif rtype == RT_COMMENT:
        _project_comment(session, raw, payload, prov)
    elif rtype in (
        RT_WORKFLOW_STATE,
        RT_ISSUE_LABEL,
        RT_CYCLE,
        RT_INITIATIVE,
        RT_ISSUE_RELATION,
    ):
        # No dedicated projection table in MVP; cursor still advances.
        pass
    else:
        _logger.debug("linear projection skip unknown resource_type=%s", rtype)


def _project_viewer(
    session: Session,
    raw: RawIngestionRecord,
    payload: dict[str, Any],
    prov: dict[str, Any],
) -> None:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    viewer = data.get("viewer") if isinstance(data, dict) else None
    if not isinstance(viewer, dict):
        return
    uid = _as_str(viewer.get("id"))
    if uid is None:
        return
    ln_upsert.upsert_linear_user(
        session,
        values={
            "tenant_id": raw.tenant_id,
            "connection_id": raw.connection_id,
            "linear_user_id": uid,
            "name": _as_str(viewer.get("name")),
            "display_name": None,
            "email": _as_str(viewer.get("email")),
            "avatar_url": None,
            "active": True,
            "guest": None,
            "admin": None,
            **prov,
        },
    )


def _project_user_node(
    session: Session,
    raw: RawIngestionRecord,
    payload: dict[str, Any],
    prov: dict[str, Any],
) -> None:
    uid = _as_str(payload.get("id"))
    if uid is None:
        return
    ln_upsert.upsert_linear_user(
        session,
        values={
            "tenant_id": raw.tenant_id,
            "connection_id": raw.connection_id,
            "linear_user_id": uid,
            "name": _as_str(payload.get("name")),
            "display_name": _as_str(payload.get("displayName")),
            "email": _as_str(payload.get("email")),
            "avatar_url": _as_str(payload.get("avatarUrl")),
            "active": _as_bool(payload.get("active")),
            "guest": _as_bool(payload.get("guest")),
            "admin": _as_bool(payload.get("admin")),
            **prov,
        },
    )


def _project_team(
    session: Session,
    raw: RawIngestionRecord,
    payload: dict[str, Any],
    prov: dict[str, Any],
) -> None:
    tid = _as_str(payload.get("id"))
    if tid is None:
        return
    ln_upsert.upsert_linear_team(
        session,
        values={
            "tenant_id": raw.tenant_id,
            "connection_id": raw.connection_id,
            "linear_team_id": tid,
            "key": _as_str(payload.get("key")),
            "name": _as_str(payload.get("name")),
            "description": _as_str(payload.get("description")),
            "private": _as_bool(payload.get("private")),
            **prov,
        },
    )


def _project_project(
    session: Session,
    raw: RawIngestionRecord,
    payload: dict[str, Any],
    prov: dict[str, Any],
) -> None:
    pid = _as_str(payload.get("id"))
    if pid is None:
        return
    ln_upsert.upsert_linear_project(
        session,
        values={
            "tenant_id": raw.tenant_id,
            "connection_id": raw.connection_id,
            "linear_project_id": pid,
            "name": _as_str(payload.get("name")),
            "slug": _as_str(payload.get("slug")),
            "description": _as_str(payload.get("description")),
            "state": _as_str(payload.get("state")),
            **prov,
        },
    )


def _project_issue(
    session: Session,
    raw: RawIngestionRecord,
    payload: dict[str, Any],
    prov: dict[str, Any],
) -> None:
    iid = _as_str(payload.get("id"))
    if iid is None:
        return
    state = _user_blob(payload.get("state"))
    team = _user_blob(payload.get("team"))
    assignee = _user_blob(payload.get("assignee"))
    creator = _user_blob(payload.get("creator"))
    project = _user_blob(payload.get("project"))
    parent = _user_blob(payload.get("parent"))
    cycle = _user_blob(payload.get("cycle"))
    labels = _labels_blob(payload)

    ln_upsert.upsert_linear_issue(
        session,
        values={
            "tenant_id": raw.tenant_id,
            "connection_id": raw.connection_id,
            "linear_issue_id": iid,
            "identifier": _as_str(payload.get("identifier")),
            "title": _as_str(payload.get("title")),
            "description": _as_str(payload.get("description")),
            "priority": _as_int(payload.get("priority")),
            "estimate": _as_float(payload.get("estimate")),
            "state_id": _as_str(state.get("id")) if state else None,
            "state_name": _as_str(state.get("name")) if state else None,
            "state_type": _as_str(state.get("type")) if state else None,
            "team_id": _as_str(team.get("id")) if team else None,
            "assignee_id": _as_str(assignee.get("id")) if assignee else None,
            "creator_id": _as_str(creator.get("id")) if creator else None,
            "project_id": _as_str(project.get("id")) if project else None,
            "parent_issue_id": _as_str(parent.get("id")) if parent else None,
            "cycle_id": _as_str(cycle.get("id")) if cycle else None,
            "labels_json": labels,
            "created_at": parse_linear_datetime(payload.get("createdAt")),
            "updated_at": parse_linear_datetime(payload.get("updatedAt")),
            "archived_at": parse_linear_datetime(payload.get("archivedAt")),
            **prov,
        },
    )


def _project_comment(
    session: Session,
    raw: RawIngestionRecord,
    payload: dict[str, Any],
    prov: dict[str, Any],
) -> None:
    cid = _as_str(payload.get("id"))
    if cid is None:
        return
    issue = _user_blob(payload.get("issue"))
    user = _user_blob(payload.get("user"))
    ln_upsert.upsert_linear_issue_comment(
        session,
        values={
            "tenant_id": raw.tenant_id,
            "connection_id": raw.connection_id,
            "linear_comment_id": cid,
            "linear_issue_id": _as_str(issue.get("id")) if issue else None,
            "issue_identifier": _as_str(issue.get("identifier")) if issue else None,
            "body": _as_str(payload.get("body")),
            "user_id": _as_str(user.get("id")) if user else None,
            "created_at": parse_linear_datetime(payload.get("createdAt")),
            "updated_at": parse_linear_datetime(payload.get("updatedAt")),
            **prov,
        },
    )
