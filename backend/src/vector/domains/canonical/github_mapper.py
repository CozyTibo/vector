"""Projections + raw row → canonical actors, artifacts, relationships (GitHub v1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from vector.domains.canonical.constants import (
    ARTIFACT_KIND_CHANGESET,
    ARTIFACT_KIND_REPOSITORY,
    ARTIFACT_KIND_REVISION,
    ARTIFACT_KIND_TRACKABLE_UNIT,
    RELATION_ASSOCIATED_WITH,
    RELATION_AUTHORED_BY,
    RELATION_CONTAINS,
    RELATIONSHIP_SOURCE_CONNECTOR,
    RULE_SOURCE_GITHUB,
    RULE_VERSION,
)
from vector.domains.canonical.orm_upsert import (
    insert_mapping_event_if_absent,
    upsert_actor,
    upsert_actor_external_identity,
    upsert_artifact,
    upsert_artifact_changeset,
    upsert_artifact_repository,
    upsert_artifact_revision,
    upsert_artifact_trackable_unit,
    upsert_current_mapping,
    upsert_external_reference,
    upsert_relationship,
)
from vector.domains.canonical.payload_hash import stable_json_hash
from vector.domains.canonical.stable_ids import (
    actor_uuid,
    artifact_uuid,
    external_reference_uuid,
    relationship_uuid,
)
from vector.domains.projections.github.external_id import (
    parse_commit_external_id,
    parse_pr_commit_link_external_id,
)
from vector.domains.projections.github.resource_types import (
    RT_COMMIT,
    RT_ISSUE,
    RT_PULL_REQUEST,
    RT_PULL_REQUEST_COMMIT,
    RT_REPOSITORY,
)
from vector.infrastructure.db.models.canonical import Relationship
from vector.infrastructure.db.models.github_projection import (
    GithubCommit,
    GithubIssue,
    GithubPullRequest,
    GithubRepository,
    GithubUser,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_GITHUB


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _github_actor_kind(gh_type: str | None) -> str:
    if gh_type and gh_type.lower() == "bot":
        return "bot"
    return "person"


def _effective_time(row: RawIngestionRecord) -> datetime:
    return row.fetched_at if row.fetched_at.tzinfo else row.fetched_at.replace(tzinfo=UTC)


def _close_open_relationships(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    subject_type: str,
    subject_id: uuid.UUID,
    object_type: str,
    object_id: uuid.UUID,
    relation_kind_id: int,
) -> None:
    session.execute(
        delete(Relationship).where(
            Relationship.tenant_id == tenant_id,
            Relationship.subject_type == subject_type,
            Relationship.subject_id == subject_id,
            Relationship.object_type == object_type,
            Relationship.object_id == object_id,
            Relationship.relation_kind_id == relation_kind_id,
            Relationship.valid_to.is_(None),
        ),
    )


def _emit_open_relationship(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    subject_type: str,
    subject_id: uuid.UUID,
    object_type: str,
    object_id: uuid.UUID,
    relation_kind_id: int,
    valid_from: datetime,
    evidence_ref: str | None,
    rule_version: str | None = None,
    rule_source: str | None = None,
) -> None:
    vf_key = valid_from.isoformat()
    rid = relationship_uuid(
        tenant_id,
        subject_type=subject_type,
        subject_id=subject_id,
        object_type=object_type,
        object_id=object_id,
        relation_kind_id=relation_kind_id,
        valid_from_key=vf_key,
    )
    _close_open_relationships(
        session,
        tenant_id=tenant_id,
        subject_type=subject_type,
        subject_id=subject_id,
        object_type=object_type,
        object_id=object_id,
        relation_kind_id=relation_kind_id,
    )
    upsert_relationship(
        session,
        id=rid,
        tenant_id=tenant_id,
        subject_type=subject_type,
        subject_id=subject_id,
        object_type=object_type,
        object_id=object_id,
        relation_kind_id=relation_kind_id,
        source=RELATIONSHIP_SOURCE_CONNECTOR,
        confidence=None,
        evidence_ref=evidence_ref,
        rule_version=rule_version if rule_version is not None else RULE_VERSION,
        rule_source=rule_source if rule_source is not None else RULE_SOURCE_GITHUB,
        valid_from=valid_from,
        valid_to=None,
    )


def ensure_github_actor(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    github_id: int,
    login: str | None,
    display_name: str | None,
    gh_type: str | None,
    last_observed_at: datetime,
    last_raw_record_id: int,
) -> uuid.UUID:
    ext_key = f"{connection_id}:user:{github_id}"
    xref_id = external_reference_uuid(tenant_id, CONNECTOR_GITHUB, ext_key)
    aid = actor_uuid(tenant_id, CONNECTOR_GITHUB, ext_key)
    payload = {
        "github_id": github_id,
        "login": login,
        "display_name": display_name,
        "type": gh_type,
    }
    ph = stable_json_hash(payload)
    effective_at = last_observed_at

    upsert_external_reference(
        session,
        id=xref_id,
        tenant_id=tenant_id,
        connector=CONNECTOR_GITHUB,
        resource_type="github.user",
        external_key=ext_key,
        connection_id=connection_id,
        last_raw_record_id=last_raw_record_id,
    )
    upsert_actor(
        session,
        id=aid,
        tenant_id=tenant_id,
        kind=_github_actor_kind(gh_type),
        display_name=display_name or login,
    )
    aei_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"vector:aei:{tenant_id}:{CONNECTOR_GITHUB}:{github_id}",
    )
    upsert_actor_external_identity(
        session,
        id=aei_id,
        tenant_id=tenant_id,
        actor_id=aid,
        connector=CONNECTOR_GITHUB,
        external_id=str(github_id),
        traits_json={"login": login, "type": gh_type},
        first_seen_at=last_observed_at,
        last_observed_at=last_observed_at,
    )

    insert_mapping_event_if_absent(
        session,
        tenant_id=tenant_id,
        external_reference_id=xref_id,
        artifact_id=None,
        actor_id=aid,
        rule_version=RULE_VERSION,
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


def ensure_github_commit_identity_actor(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    external_identity: str,
    display_name: str | None,
    last_observed_at: datetime,
    last_raw_record_id: int,
) -> uuid.UUID:
    ext_key = external_identity
    xref_id = external_reference_uuid(tenant_id, CONNECTOR_GITHUB, ext_key)
    aid = actor_uuid(tenant_id, CONNECTOR_GITHUB, ext_key)
    payload = {
        "external_identity": external_identity,
        "display_name": display_name,
        "synthetic": True,
        "source": "github_commit_identity",
    }
    ph = stable_json_hash(payload)
    effective_at = last_observed_at

    upsert_external_reference(
        session,
        id=xref_id,
        tenant_id=tenant_id,
        connector=CONNECTOR_GITHUB,
        resource_type="github.commit_author",
        external_key=ext_key,
        connection_id=connection_id,
        last_raw_record_id=last_raw_record_id,
    )
    upsert_actor(
        session,
        id=aid,
        tenant_id=tenant_id,
        kind="person",
        display_name=display_name,
    )
    aei_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"vector:aei:{tenant_id}:{CONNECTOR_GITHUB}:{external_identity}",
    )
    upsert_actor_external_identity(
        session,
        id=aei_id,
        tenant_id=tenant_id,
        actor_id=aid,
        connector=CONNECTOR_GITHUB,
        external_id=external_identity,
        traits_json={"synthetic": True, "source": "github_commit_identity"},
        first_seen_at=last_observed_at,
        last_observed_at=last_observed_at,
    )
    insert_mapping_event_if_absent(
        session,
        tenant_id=tenant_id,
        external_reference_id=xref_id,
        artifact_id=None,
        actor_id=aid,
        rule_version=RULE_VERSION,
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


def _commit_author_identity_external_id(
    *,
    author_name: str | None,
    author_email: str | None,
) -> str | None:
    email = (author_email or "").strip().lower()
    if email:
        return f"commit_author:{email}"
    name = (author_name or "").strip().lower()
    if name:
        return f"commit_author:name:{name}"
    return None


def _repo_github_id_by_full_name(
    session: Session,
    connection_id: uuid.UUID,
    full_name: str,
) -> int | None:
    fn = full_name.strip().lower()
    q = select(GithubRepository.repository_github_id).where(
        GithubRepository.connection_id == connection_id,
        func.lower(GithubRepository.full_name) == fn,
    )
    return session.scalar(q)


def _upsert_artifact_with_mapping(
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
    xref_id = external_reference_uuid(tenant_id, CONNECTOR_GITHUB, external_key)
    ph = stable_json_hash(mapping_payload)
    effective_at = last_observed_at

    upsert_external_reference(
        session,
        id=xref_id,
        tenant_id=tenant_id,
        connector=CONNECTOR_GITHUB,
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
        rule_version=RULE_VERSION,
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


def handle_github_canonical_row(session: Session, raw: RawIngestionRecord) -> None:
    if raw.connector != CONNECTOR_GITHUB:
        return
    if not (200 <= raw.http_status <= 299):
        return

    rtype = raw.resource_type
    if rtype == RT_REPOSITORY:
        _map_repository(session, raw)
    elif rtype == RT_PULL_REQUEST:
        _map_pull_request(session, raw)
    elif rtype == RT_PULL_REQUEST_COMMIT:
        _map_pr_commit_link(session, raw)
    elif rtype == RT_ISSUE:
        _map_issue(session, raw)
    elif rtype == RT_COMMIT:
        _map_commit(session, raw)


def _map_repository(session: Session, raw: RawIngestionRecord) -> None:
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}
    rid = _as_int(payload.get("id"))
    if rid is None:
        return
    ext_key = f"{raw.connection_id}:repo:{rid}"
    aid = artifact_uuid(raw.tenant_id, CONNECTOR_GITHUB, ext_key)
    title = payload.get("full_name") if isinstance(payload.get("full_name"), str) else None
    summary = payload.get("description") if isinstance(payload.get("description"), str) else None
    mapping_payload = {
        "kind": "repository",
        "repository_github_id": rid,
        "full_name": title,
    }
    _upsert_artifact_with_mapping(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        external_key=ext_key,
        resource_type=RT_REPOSITORY,
        artifact_kind_id=ARTIFACT_KIND_REPOSITORY,
        title=title,
        summary=summary,
        status=None,
        last_observed_at=_effective_time(raw),
        last_raw_record_id=raw.id,
        mapping_payload=mapping_payload,
        artifact_id=aid,
    )
    upsert_artifact_repository(
        session,
        artifact_id=aid,
        repository_github_id=rid,
        full_name=title,
    )


def _map_pull_request(session: Session, raw: RawIngestionRecord) -> None:
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}
    base = payload.get("base")
    base_repo = base.get("repo") if isinstance(base, dict) else None
    repo_github_id = _as_int(base_repo.get("id")) if isinstance(base_repo, dict) else None
    num = _as_int(payload.get("number"))
    if repo_github_id is None or num is None:
        return
    pr_row = session.get(
        GithubPullRequest,
        (raw.connection_id, repo_github_id, num),
    )
    if pr_row is None:
        return

    repo_ext_key = f"{raw.connection_id}:repo:{repo_github_id}"
    repo_artifact_id = artifact_uuid(raw.tenant_id, CONNECTOR_GITHUB, repo_ext_key)
    _ensure_repo_artifact(session, raw, pr_row.repository_github_id, pr_row.repo_full_name)

    ext_key = f"{raw.connection_id}:pr:{repo_github_id}:{num}"
    aid = artifact_uuid(raw.tenant_id, CONNECTOR_GITHUB, ext_key)
    mapping_payload = {
        "kind": "changeset",
        "repository_github_id": repo_github_id,
        "number": num,
        "head_sha": pr_row.head_sha,
    }
    _upsert_artifact_with_mapping(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        external_key=ext_key,
        resource_type=RT_PULL_REQUEST,
        artifact_kind_id=ARTIFACT_KIND_CHANGESET,
        title=pr_row.title,
        summary=pr_row.body,
        status=pr_row.state,
        last_observed_at=pr_row.last_observed_at,
        last_raw_record_id=raw.id,
        mapping_payload=mapping_payload,
        artifact_id=aid,
    )
    upsert_artifact_changeset(
        session,
        artifact_id=aid,
        repository_github_id=repo_github_id,
        number=num,
        head_sha=pr_row.head_sha,
        repo_full_name=pr_row.repo_full_name,
    )

    vf = pr_row.github_updated_at or pr_row.last_observed_at
    _emit_open_relationship(
        session,
        tenant_id=raw.tenant_id,
        subject_type="artifact",
        subject_id=aid,
        object_type="artifact",
        object_id=repo_artifact_id,
        relation_kind_id=RELATION_ASSOCIATED_WITH,
        valid_from=vf,
        evidence_ref=f"github_pull_request:{repo_github_id}:{num}",
    )

    author_gid = pr_row.author_github_id
    if author_gid is not None:
        act = ensure_github_actor(
            session,
            tenant_id=raw.tenant_id,
            connection_id=raw.connection_id,
            github_id=author_gid,
            login=pr_row.author_login,
            display_name=pr_row.author_login,
            gh_type="User",
            last_observed_at=pr_row.last_observed_at,
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
            evidence_ref=f"github_pull_request:{repo_github_id}:{num}",
        )


def _map_pr_commit_link(session: Session, raw: RawIngestionRecord) -> None:
    parsed = parse_pr_commit_link_external_id(raw.external_id)
    if parsed is None:
        return
    full_name, num, sha = parsed
    repo_github_id = _repo_github_id_by_full_name(session, raw.connection_id, full_name)
    if repo_github_id is None:
        return
    pr_row = session.get(
        GithubPullRequest,
        (raw.connection_id, repo_github_id, num),
    )
    if pr_row is None:
        return

    _ensure_repo_artifact(session, raw, repo_github_id, pr_row.repo_full_name)

    pr_ext_key = f"{raw.connection_id}:pr:{repo_github_id}:{num}"
    pr_aid = artifact_uuid(raw.tenant_id, CONNECTOR_GITHUB, pr_ext_key)
    commit_ext_key = f"{raw.connection_id}:commit:{repo_github_id}:{sha}"
    commit_aid = artifact_uuid(raw.tenant_id, CONNECTOR_GITHUB, commit_ext_key)

    vf = pr_row.github_updated_at or pr_row.last_observed_at or _effective_time(raw)
    _emit_open_relationship(
        session,
        tenant_id=raw.tenant_id,
        subject_type="artifact",
        subject_id=pr_aid,
        object_type="artifact",
        object_id=commit_aid,
        relation_kind_id=RELATION_CONTAINS,
        valid_from=vf,
        evidence_ref=f"github_pr_commit:{repo_github_id}:{num}:{sha}",
    )


def _ensure_repo_artifact(
    session: Session,
    raw: RawIngestionRecord,
    repository_github_id: int,
    full_name: str | None,
) -> uuid.UUID:
    ext_key = f"{raw.connection_id}:repo:{repository_github_id}"
    aid = artifact_uuid(raw.tenant_id, CONNECTOR_GITHUB, ext_key)
    mapping_payload = {
        "kind": "repository",
        "repository_github_id": repository_github_id,
        "full_name": full_name,
    }
    _upsert_artifact_with_mapping(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        external_key=ext_key,
        resource_type=RT_REPOSITORY,
        artifact_kind_id=ARTIFACT_KIND_REPOSITORY,
        title=full_name,
        summary=None,
        status=None,
        last_observed_at=_effective_time(raw),
        last_raw_record_id=raw.id,
        mapping_payload=mapping_payload,
        artifact_id=aid,
    )
    upsert_artifact_repository(
        session,
        artifact_id=aid,
        repository_github_id=repository_github_id,
        full_name=full_name,
    )
    return aid


def _map_issue(session: Session, raw: RawIngestionRecord) -> None:
    body = raw.payload_body
    if isinstance(body, dict) and isinstance(body.get("pull_request"), dict):
        return
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}
    repo_obj = payload.get("repository")
    repo_github_id = _as_int(repo_obj.get("id")) if isinstance(repo_obj, dict) else None
    num = _as_int(payload.get("number"))
    if repo_github_id is None or num is None:
        return
    issue_row = session.get(
        GithubIssue,
        (raw.connection_id, repo_github_id, num),
    )
    if issue_row is None:
        return

    _ensure_repo_artifact(session, raw, repo_github_id, issue_row.repo_full_name)
    repo_ext_key = f"{raw.connection_id}:repo:{repo_github_id}"
    repo_artifact_id = artifact_uuid(raw.tenant_id, CONNECTOR_GITHUB, repo_ext_key)

    ext_key = f"{raw.connection_id}:issue:{repo_github_id}:{num}"
    aid = artifact_uuid(raw.tenant_id, CONNECTOR_GITHUB, ext_key)
    key = f"{issue_row.repo_full_name or ''}#{num}".strip()
    mapping_payload = {
        "kind": "trackable_unit",
        "repository_github_id": repo_github_id,
        "number": num,
    }
    _upsert_artifact_with_mapping(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        external_key=ext_key,
        resource_type=RT_ISSUE,
        artifact_kind_id=ARTIFACT_KIND_TRACKABLE_UNIT,
        title=issue_row.title,
        summary=issue_row.body,
        status=issue_row.state,
        last_observed_at=issue_row.last_observed_at,
        last_raw_record_id=raw.id,
        mapping_payload=mapping_payload,
        artifact_id=aid,
    )
    upsert_artifact_trackable_unit(
        session,
        artifact_id=aid,
        provider="github",
        key=key or None,
        url=issue_row.html_url,
        repository_github_id=repo_github_id,
        issue_number=num,
    )

    vf = issue_row.github_updated_at or issue_row.last_observed_at
    _emit_open_relationship(
        session,
        tenant_id=raw.tenant_id,
        subject_type="artifact",
        subject_id=aid,
        object_type="artifact",
        object_id=repo_artifact_id,
        relation_kind_id=RELATION_ASSOCIATED_WITH,
        valid_from=vf,
        evidence_ref=f"github_issue:{repo_github_id}:{num}",
    )

    author_gid = issue_row.author_github_id
    if author_gid is not None:
        act = ensure_github_actor(
            session,
            tenant_id=raw.tenant_id,
            connection_id=raw.connection_id,
            github_id=author_gid,
            login=issue_row.author_login,
            display_name=issue_row.author_login,
            gh_type="User",
            last_observed_at=issue_row.last_observed_at,
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
            evidence_ref=f"github_issue:{repo_github_id}:{num}",
        )


def _map_commit(session: Session, raw: RawIngestionRecord) -> None:
    payload = raw.payload_body if isinstance(raw.payload_body, dict) else {}
    repo_obj = payload.get("repository")
    repo_github_id = _as_int(repo_obj.get("id")) if isinstance(repo_obj, dict) else None
    sha_val: str | None = None
    head_sha = payload.get("sha")
    if isinstance(head_sha, str) and len(head_sha) >= 7:
        sha_val = head_sha
    parsed = parse_commit_external_id(raw.external_id)
    if parsed is not None:
        full_name, sha_from_ext = parsed
        if sha_val is None:
            sha_val = sha_from_ext
        if repo_github_id is None:
            repo_github_id = _repo_github_id_by_full_name(session, raw.connection_id, full_name)
    if repo_github_id is None or sha_val is None:
        return

    commit_row = session.get(
        GithubCommit,
        (raw.connection_id, repo_github_id, sha_val),
    )
    if commit_row is None:
        return

    _ensure_repo_artifact(session, raw, repo_github_id, commit_row.repo_full_name)
    repo_ext_key = f"{raw.connection_id}:repo:{repo_github_id}"
    repo_artifact_id = artifact_uuid(raw.tenant_id, CONNECTOR_GITHUB, repo_ext_key)

    ext_key = f"{raw.connection_id}:commit:{repo_github_id}:{sha_val}"
    aid = artifact_uuid(raw.tenant_id, CONNECTOR_GITHUB, ext_key)
    mapping_payload = {
        "kind": "revision",
        "repository_github_id": repo_github_id,
        "sha": sha_val,
    }
    _upsert_artifact_with_mapping(
        session,
        tenant_id=raw.tenant_id,
        connection_id=raw.connection_id,
        external_key=ext_key,
        resource_type=RT_COMMIT,
        artifact_kind_id=ARTIFACT_KIND_REVISION,
        title=sha_val[:7],
        summary=commit_row.message,
        status=None,
        last_observed_at=commit_row.last_observed_at,
        last_raw_record_id=raw.id,
        mapping_payload=mapping_payload,
        artifact_id=aid,
    )
    upsert_artifact_revision(
        session,
        artifact_id=aid,
        repository_github_id=repo_github_id,
        sha=sha_val,
        repo_full_name=commit_row.repo_full_name,
    )

    vf = commit_row.last_observed_at
    _emit_open_relationship(
        session,
        tenant_id=raw.tenant_id,
        subject_type="artifact",
        subject_id=aid,
        object_type="artifact",
        object_id=repo_artifact_id,
        relation_kind_id=RELATION_ASSOCIATED_WITH,
        valid_from=vf,
        evidence_ref=f"github_commit:{repo_github_id}:{sha_val}",
    )

    author_gid = commit_row.author_github_id
    if author_gid is not None:
        display_name = commit_row.author_name or commit_row.committer_name
        login: str | None = None
        gu = session.get(GithubUser, (raw.connection_id, author_gid))
        if gu is not None:
            login = gu.login
        act = ensure_github_actor(
            session,
            tenant_id=raw.tenant_id,
            connection_id=raw.connection_id,
            github_id=author_gid,
            login=login,
            display_name=display_name,
            gh_type="User",
            last_observed_at=commit_row.last_observed_at,
            last_raw_record_id=raw.id,
        )
    else:
        external_identity = _commit_author_identity_external_id(
            author_name=commit_row.author_name,
            author_email=commit_row.author_email,
        )
        if external_identity is not None:
            display_name = commit_row.author_name or commit_row.author_email
            act = ensure_github_commit_identity_actor(
                session,
                tenant_id=raw.tenant_id,
                connection_id=raw.connection_id,
                external_identity=external_identity,
                display_name=display_name,
                last_observed_at=commit_row.last_observed_at,
                last_raw_record_id=raw.id,
            )
        else:
            committer_gid = commit_row.committer_github_id
            if committer_gid is None:
                return
            display_name = commit_row.committer_name
            login = None
            gu = session.get(GithubUser, (raw.connection_id, committer_gid))
            if gu is not None:
                login = gu.login
            act = ensure_github_actor(
                session,
                tenant_id=raw.tenant_id,
                connection_id=raw.connection_id,
                github_id=committer_gid,
                login=login,
                display_name=display_name,
                gh_type="User",
                last_observed_at=commit_row.last_observed_at,
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
        evidence_ref=f"github_commit:{repo_github_id}:{sha_val}",
    )