"""Linear raw rows + projection tables → canonical actors, artifacts, relationships (v1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.canonical.constants import (
    ARTIFACT_KIND_TRACKABLE_UNIT,
    RELATION_ASSIGNED_TO,
    RELATION_ASSOCIATED_WITH,
    RELATION_AUTHORED_BY,
    RELATION_COMMENTED_ON,
    RELATION_CONTAINS,
    RULE_SOURCE_LINEAR,
    RULE_VERSION_LINEAR,
)
from vector.domains.canonical.github_mapper import _emit_open_relationship
from vector.domains.canonical.orm_upsert import (
    insert_mapping_event_if_absent,
    upsert_actor,
    upsert_actor_external_identity,
    upsert_artifact,
    upsert_artifact_trackable_unit,
    upsert_current_mapping,
    upsert_external_reference,
)
from vector.domains.canonical.payload_hash import stable_json_hash
from vector.domains.canonical.stable_ids import actor_uuid, artifact_uuid, external_reference_uuid
from vector.domains.projections.linear.resource_types import (
    RT_COMMENT,
    RT_ISSUE,
    RT_PROJECT,
    RT_TEAM,
    RT_USER,
    RT_VIEWER,
)
from vector.infrastructure.db.models.linear_projection import (
    LinearIssue,
    LinearIssueComment,
    LinearProject,
    LinearTeam,
    LinearUser,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_LINEAR


def _as_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _effective_time(row: RawIngestionRecord) -> datetime:
    return row.fetched_at if row.fetched_at.tzinfo else row.fetched_at.replace(tzinfo=UTC)


def _upsert_artifact_with_mapping_linear(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    external_key: str,
    resource_type: str,
    artifact_kind_id: int,
    title: str | None,
    summary: str | None,
    status: str | None,
    last_observed_at: datetime,
    last_raw_record_id: int,
    mapping_payload: dict[str, Any],
    artifact_id: uuid.UUID,
) -> uuid.UUID:
    xref_id = external_reference_uuid(tenant_id, CONNECTOR_LINEAR, external_key)
    ph = stable_json_hash(mapping_payload)
    effective_at = last_observed_at

    upsert_external_reference(
        session,
        id=xref_id,
        tenant_id=tenant_id,
        connector=CONNECTOR_LINEAR,
        resource_type=resource_type,
        external_key=external_key,
        connection_id=connection_id,
        last_raw_record_id=last_raw_record_id,
    )
    upsert_artifact(
        session,
        id=artifact_id,
        tenant_id=tenant_id,
        artifact_kind_id=artifact_kind_id,
        title=title,
        summary=summary,
        status=status,
        last_observed_at=last_observed_at,
    )
    insert_mapping_event_if_absent(
        session,
        tenant_id=tenant_id,
        external_reference_id=xref_id,
        artifact_id=artifact_id,
        actor_id=None,
        rule_version=RULE_VERSION_LINEAR,
        effective_at=effective_at,
        payload_hash=ph,
    )
    upsert_current_mapping(
        session,
        external_reference_id=xref_id,
        tenant_id=tenant_id,
        artifact_id=artifact_id,
        actor_id=None,
    )
    return artifact_id


def ensure_linear_actor(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    linear_user_id: str,
    display_name: str | None,
    name: str | None,
    email: str | None,
    last_observed_at: datetime,
    last_raw_record_id: int,
) -> uuid.UUID:
    ext_key = f"{connection_id}:user:{linear_user_id}"
    xref_id = external_reference_uuid(tenant_id, CONNECTOR_LINEAR, ext_key)
    aid = actor_uuid(tenant_id, CONNECTOR_LINEAR, ext_key)
    payload = {
        "linear_user_id": linear_user_id,
        "name": name,
        "display_name": display_name,
        "email": email,
    }
    ph = stable_json_hash(payload)
    effective_at = last_observed_at

    upsert_external_reference(
        session,
        id=xref_id,
        tenant_id=tenant_id,
        connector=CONNECTOR_LINEAR,
        resource_type="linear.user",
        external_key=ext_key,
        connection_id=connection_id,
        last_raw_record_id=last_raw_record_id,
    )
    upsert_actor(
        session,
        id=aid,
        tenant_id=tenant_id,
        kind="person",
        display_name=display_name or name or email or linear_user_id[:8],
    )
    aei_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"vector:aei:{tenant_id}:{CONNECTOR_LINEAR}:{linear_user_id}",
    )
    upsert_actor_external_identity(
        session,
        id=aei_id,
        tenant_id=tenant_id,
        actor_id=aid,
        connector=CONNECTOR_LINEAR,
        external_id=linear_user_id,
        traits_json={"name": name, "email": email},
        first_seen_at=last_observed_at,
        last_observed_at=last_observed_at,
    )

    insert_mapping_event_if_absent(
        session,
        tenant_id=tenant_id,
        external_reference_id=xref_id,
        artifact_id=None,
        actor_id=aid,
        rule_version=RULE_VERSION_LINEAR,
        effective_at=effective_at,
        payload_hash=ph,
    )
    upsert_current_mapping(
        session,
        external_reference_id=xref_id,
        tenant_id=tenant_id,
        artifact_id=None,
        actor_id=aid,
    )
    return aid


def _resolve_user_blob(raw: RawIngestionRecord) -> dict[str, Any] | None:
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}
    if raw.resource_type == RT_VIEWER:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        viewer = data.get("viewer")
        return viewer if isinstance(viewer, dict) else None
    return payload


def _map_linear_user_from_payload(session: Session, raw: RawIngestionRecord) -> None:
    u = _resolve_user_blob(raw)
    if u is None:
        return
    uid = _as_str(u.get("id"))
    if uid is None:
        return
    row = session.get(LinearUser, (raw.connection_id, uid))
    display_name = row.display_name if row else _as_str(u.get("displayName"))
    name = row.name if row else _as_str(u.get("name"))
    email = row.email if row else _as_str(u.get("email"))
    last_obs = row.last_observed_at if row else _effective_time(raw)
    ensure_linear_actor(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        linear_user_id=uid,
        display_name=display_name,
        name=name,
        email=email,
        last_observed_at=last_obs,
        last_raw_record_id=raw.id,
    )


def _ensure_linear_team_artifact(
    session: Session,
    raw: RawIngestionRecord,
    team: LinearTeam,
) -> uuid.UUID:
    tid = team.linear_team_id
    ext_key = f"{raw.connection_id}:team:{tid}"
    aid = artifact_uuid(raw.tenant_id, CONNECTOR_LINEAR, ext_key)
    mapping_payload = {
        "kind": "linear_team",
        "linear_team_id": tid,
        "key": team.key,
    }
    _upsert_artifact_with_mapping_linear(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        external_key=ext_key,
        resource_type=RT_TEAM,
        artifact_kind_id=ARTIFACT_KIND_TRACKABLE_UNIT,
        title=team.name or team.key,
        summary=team.description,
        status=None,
        last_observed_at=team.last_observed_at,
        last_raw_record_id=raw.id,
        mapping_payload=mapping_payload,
        artifact_id=aid,
    )
    upsert_artifact_trackable_unit(
        session,
        artifact_id=aid,
        provider="linear",
        key=team.key or tid,
        url=None,
        repository_github_id=None,
        issue_number=None,
    )
    return aid


def _upsert_linear_issue_artifact_core(
    session: Session,
    raw: RawIngestionRecord,
    issue_row: LinearIssue,
) -> uuid.UUID:
    iid = issue_row.linear_issue_id
    ext_key = f"{raw.connection_id}:issue:{iid}"
    aid = artifact_uuid(raw.tenant_id, CONNECTOR_LINEAR, ext_key)
    mapping_payload = {
        "kind": "linear_issue",
        "linear_issue_id": iid,
        "identifier": issue_row.identifier,
    }
    _upsert_artifact_with_mapping_linear(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        external_key=ext_key,
        resource_type=RT_ISSUE,
        artifact_kind_id=ARTIFACT_KIND_TRACKABLE_UNIT,
        title=issue_row.title,
        summary=issue_row.description,
        status=issue_row.state_name,
        last_observed_at=issue_row.last_observed_at,
        last_raw_record_id=raw.id,
        mapping_payload=mapping_payload,
        artifact_id=aid,
    )
    upsert_artifact_trackable_unit(
        session,
        artifact_id=aid,
        provider="linear",
        key=issue_row.identifier or iid,
        url=None,
        repository_github_id=None,
        issue_number=None,
    )
    return aid


def _ensure_linear_project_artifact(
    session: Session,
    raw: RawIngestionRecord,
    proj: LinearProject,
) -> uuid.UUID:
    ext_key = f"{raw.connection_id}:project:{proj.linear_project_id}"
    aid = artifact_uuid(raw.tenant_id, CONNECTOR_LINEAR, ext_key)
    mapping_payload = {
        "kind": "linear_project",
        "linear_project_id": proj.linear_project_id,
        "slug": proj.slug,
    }
    _upsert_artifact_with_mapping_linear(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        external_key=ext_key,
        resource_type=RT_PROJECT,
        artifact_kind_id=ARTIFACT_KIND_TRACKABLE_UNIT,
        title=proj.name,
        summary=proj.description,
        status=proj.state,
        last_observed_at=proj.last_observed_at,
        last_raw_record_id=raw.id,
        mapping_payload=mapping_payload,
        artifact_id=aid,
    )
    upsert_artifact_trackable_unit(
        session,
        artifact_id=aid,
        provider="linear",
        key=proj.slug or proj.linear_project_id,
        url=None,
        repository_github_id=None,
        issue_number=None,
    )
    return aid


def _map_linear_project(session: Session, raw: RawIngestionRecord) -> None:
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}
    pid = _as_str(payload.get("id"))
    if pid is None:
        return
    proj = session.get(LinearProject, (raw.connection_id, pid))
    if proj is None:
        return
    _ensure_linear_project_artifact(session, raw, proj)


def _map_linear_team(session: Session, raw: RawIngestionRecord) -> None:
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}
    tid = _as_str(payload.get("id"))
    if tid is None:
        return
    team = session.get(LinearTeam, (raw.connection_id, tid))
    if team is None:
        return
    _ensure_linear_team_artifact(session, raw, team)


def _map_linear_issue(session: Session, raw: RawIngestionRecord) -> None:
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}
    iid = _as_str(payload.get("id"))
    if iid is None:
        return
    issue_row = session.get(LinearIssue, (raw.connection_id, iid))
    if issue_row is None:
        return

    project_aid: uuid.UUID | None = None
    if issue_row.project_id:
        proj = session.get(LinearProject, (raw.connection_id, issue_row.project_id))
        if proj is not None:
            project_aid = _ensure_linear_project_artifact(session, raw, proj)

    aid = _upsert_linear_issue_artifact_core(session, raw, issue_row)

    vf = issue_row.updated_at or issue_row.last_observed_at
    if project_aid is not None:
        _emit_open_relationship(
            session,
            tenant_id=raw.tenant_id,
            subject_type="artifact",
            subject_id=aid,
            object_type="artifact",
            object_id=project_aid,
            relation_kind_id=RELATION_ASSOCIATED_WITH,
            valid_from=vf,
            evidence_ref=f"linear_issue:{iid}:project",
            rule_version=RULE_VERSION_LINEAR,
            rule_source=RULE_SOURCE_LINEAR,
        )

    if issue_row.team_id:
        team = session.get(LinearTeam, (raw.connection_id, issue_row.team_id))
        if team is not None:
            team_aid = _ensure_linear_team_artifact(session, raw, team)
            _emit_open_relationship(
                session,
                tenant_id=raw.tenant_id,
                subject_type="artifact",
                subject_id=aid,
                object_type="artifact",
                object_id=team_aid,
                relation_kind_id=RELATION_ASSOCIATED_WITH,
                valid_from=vf,
                evidence_ref=f"linear_issue:{iid}:team",
                rule_version=RULE_VERSION_LINEAR,
                rule_source=RULE_SOURCE_LINEAR,
            )

    if issue_row.parent_issue_id:
        parent_row = session.get(LinearIssue, (raw.connection_id, issue_row.parent_issue_id))
        if parent_row is not None:
            parent_aid = _upsert_linear_issue_artifact_core(session, raw, parent_row)
            _emit_open_relationship(
                session,
                tenant_id=raw.tenant_id,
                subject_type="artifact",
                subject_id=parent_aid,
                object_type="artifact",
                object_id=aid,
                relation_kind_id=RELATION_CONTAINS,
                valid_from=vf,
                evidence_ref=f"linear_issue:{iid}:parent",
                rule_version=RULE_VERSION_LINEAR,
                rule_source=RULE_SOURCE_LINEAR,
            )

    if issue_row.creator_id:
        creator = session.get(LinearUser, (raw.connection_id, issue_row.creator_id))
        act = ensure_linear_actor(
            session,
            tenant_id=raw.tenant_id,
            connection_id=raw.connection_id,
            linear_user_id=issue_row.creator_id,
            display_name=creator.display_name if creator else None,
            name=creator.name if creator else None,
            email=creator.email if creator else None,
            last_observed_at=creator.last_observed_at if creator else issue_row.last_observed_at,
            last_raw_record_id=raw.id,
        )
        _emit_open_relationship(
            session,
            tenant_id=raw.tenant_id,
            subject_type="actor",
            subject_id=act,
            object_type="artifact",
            object_id=aid,
            relation_kind_id=RELATION_AUTHORED_BY,
            valid_from=vf,
            evidence_ref=f"linear_issue:{iid}:creator",
            rule_version=RULE_VERSION_LINEAR,
            rule_source=RULE_SOURCE_LINEAR,
        )

    if issue_row.assignee_id:
        assignee = session.get(LinearUser, (raw.connection_id, issue_row.assignee_id))
        assign_actor = ensure_linear_actor(
            session,
            tenant_id=raw.tenant_id,
            connection_id=raw.connection_id,
            linear_user_id=issue_row.assignee_id,
            display_name=assignee.display_name if assignee else None,
            name=assignee.name if assignee else None,
            email=assignee.email if assignee else None,
            last_observed_at=assignee.last_observed_at if assignee else issue_row.last_observed_at,
            last_raw_record_id=raw.id,
        )
        _emit_open_relationship(
            session,
            tenant_id=raw.tenant_id,
            subject_type="actor",
            subject_id=assign_actor,
            object_type="artifact",
            object_id=aid,
            relation_kind_id=RELATION_ASSIGNED_TO,
            valid_from=vf,
            evidence_ref=f"linear_issue:{iid}:assignee",
            rule_version=RULE_VERSION_LINEAR,
            rule_source=RULE_SOURCE_LINEAR,
        )


def _map_linear_comment(session: Session, raw: RawIngestionRecord) -> None:
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}
    cid = _as_str(payload.get("id"))
    if cid is None:
        return
    row = session.get(LinearIssueComment, (raw.connection_id, cid))
    if row is None or not row.linear_issue_id:
        return
    issue_row = session.get(LinearIssue, (raw.connection_id, row.linear_issue_id))
    if issue_row is None:
        return
    issue_aid = _upsert_linear_issue_artifact_core(session, raw, issue_row)
    vf = row.updated_at or row.last_observed_at
    if not row.user_id:
        return
    user_row = session.get(LinearUser, (raw.connection_id, row.user_id))
    act = ensure_linear_actor(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        linear_user_id=row.user_id,
        display_name=user_row.display_name if user_row else None,
        name=user_row.name if user_row else None,
        email=user_row.email if user_row else None,
        last_observed_at=user_row.last_observed_at if user_row else row.last_observed_at,
        last_raw_record_id=raw.id,
    )
    _emit_open_relationship(
        session,
        tenant_id=raw.tenant_id,
        subject_type="actor",
        subject_id=act,
        object_type="artifact",
        object_id=issue_aid,
        relation_kind_id=RELATION_COMMENTED_ON,
        valid_from=vf,
        evidence_ref=f"linear_comment:{cid}:issue:{row.linear_issue_id}",
        rule_version=RULE_VERSION_LINEAR,
        rule_source=RULE_SOURCE_LINEAR,
    )


def handle_linear_canonical_row(session: Session, raw: RawIngestionRecord) -> None:
    if raw.connector != CONNECTOR_LINEAR:
        return
    if not (200 <= raw.http_status <= 299):
        return

    rtype = raw.resource_type
    if rtype in (RT_USER, RT_VIEWER):
        _map_linear_user_from_payload(session, raw)
    elif rtype == RT_PROJECT:
        _map_linear_project(session, raw)
    elif rtype == RT_ISSUE:
        _map_linear_issue(session, raw)
    elif rtype == RT_COMMENT:
        _map_linear_comment(session, raw)
    elif rtype == RT_TEAM:
        _map_linear_team(session, raw)
