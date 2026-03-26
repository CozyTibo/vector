"""PostgreSQL upserts for canonical tables — safe under concurrent Step 3 drains."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.canonical import (
    Actor,
    ActorExternalIdentity,
    Artifact,
    ArtifactChangeset,
    ArtifactRepository,
    ArtifactRevision,
    ArtifactTrackableUnit,
    CurrentMapping,
    ExternalReference,
    MappingEvent,
    Relationship,
)


def insert_mapping_event_if_absent(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    external_reference_id: uuid.UUID,
    artifact_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
    rule_version: str,
    effective_at: datetime,
    payload_hash: str,
) -> None:
    """Append-only mapping_event; duplicates are ignored (partial unique index)."""
    stmt = (
        pg_insert(MappingEvent)
        .values(
            tenant_id=tenant_id,
            external_reference_id=external_reference_id,
            artifact_id=artifact_id,
            actor_id=actor_id,
            rule_version=rule_version,
            effective_at=effective_at,
            payload_hash=payload_hash,
            supersedes_event_id=None,
        )
        .on_conflict_do_nothing(
            index_elements=[
                MappingEvent.external_reference_id,
                MappingEvent.rule_version,
                MappingEvent.payload_hash,
            ],
            index_where=MappingEvent.payload_hash.isnot(None),
        )
    )
    session.execute(stmt)


def upsert_actor(
    session: Session,
    *,
    id: uuid.UUID,
    tenant_id: uuid.UUID,
    kind: str,
    display_name: str | None,
) -> None:
    stmt = (
        pg_insert(Actor)
        .values(
            id=id,
            tenant_id=tenant_id,
            kind=kind,
            display_name=display_name,
        )
        .on_conflict_do_update(
            index_elements=[Actor.id],
            set_={
                "kind": kind,
                "display_name": display_name,
                "updated_at": func.now(),
            },
        )
    )
    session.execute(stmt)


def upsert_external_reference(
    session: Session,
    *,
    id: uuid.UUID,
    tenant_id: uuid.UUID,
    connector: str,
    resource_type: str | None,
    external_key: str,
    connection_id: uuid.UUID | None,
    last_raw_record_id: int | None,
) -> None:
    stmt = (
        pg_insert(ExternalReference)
        .values(
            id=id,
            tenant_id=tenant_id,
            connector=connector,
            resource_type=resource_type,
            external_key=external_key,
            connection_id=connection_id,
            last_raw_record_id=last_raw_record_id,
        )
        .on_conflict_do_update(
            constraint="uq_external_reference_tenant_connector_key",
            set_={
                "resource_type": resource_type,
                "connection_id": connection_id,
                "last_raw_record_id": last_raw_record_id,
            },
        )
    )
    session.execute(stmt)


def upsert_artifact(
    session: Session,
    *,
    id: uuid.UUID,
    tenant_id: uuid.UUID,
    artifact_kind_id: int,
    title: str | None,
    summary: str | None,
    status: str | None,
    last_observed_at: datetime | None,
) -> None:
    stmt = (
        pg_insert(Artifact)
        .values(
            id=id,
            tenant_id=tenant_id,
            artifact_kind_id=artifact_kind_id,
            title=title,
            summary=summary,
            status=status,
            last_observed_at=last_observed_at,
        )
        .on_conflict_do_update(
            index_elements=[Artifact.id],
            set_={
                "artifact_kind_id": artifact_kind_id,
                "title": title,
                "summary": summary,
                "status": status,
                "last_observed_at": last_observed_at,
            },
        )
    )
    session.execute(stmt)


def upsert_actor_external_identity(
    session: Session,
    *,
    id: uuid.UUID,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    connector: str,
    external_id: str,
    traits_json: dict[str, Any] | None,
    first_seen_at: datetime | None,
    last_observed_at: datetime | None,
) -> None:
    stmt = (
        pg_insert(ActorExternalIdentity)
        .values(
            id=id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            connector=connector,
            external_id=external_id,
            traits_json=traits_json,
            first_seen_at=first_seen_at,
            last_observed_at=last_observed_at,
        )
        .on_conflict_do_update(
            constraint="uq_actor_external_identity_tenant_connector_ext",
            set_={
                "actor_id": actor_id,
                "traits_json": traits_json,
                "last_observed_at": last_observed_at,
            },
        )
    )
    session.execute(stmt)


def upsert_current_mapping(
    session: Session,
    *,
    external_reference_id: uuid.UUID,
    tenant_id: uuid.UUID,
    artifact_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
) -> None:
    stmt = (
        pg_insert(CurrentMapping)
        .values(
            external_reference_id=external_reference_id,
            tenant_id=tenant_id,
            artifact_id=artifact_id,
            actor_id=actor_id,
            updated_at=func.now(),
        )
        .on_conflict_do_update(
            index_elements=[CurrentMapping.external_reference_id],
            set_={
                "tenant_id": tenant_id,
                "artifact_id": artifact_id,
                "actor_id": actor_id,
                "updated_at": func.now(),
            },
        )
    )
    session.execute(stmt)


def upsert_artifact_repository(
    session: Session,
    *,
    artifact_id: uuid.UUID,
    repository_github_id: int,
    full_name: str | None,
) -> None:
    stmt = (
        pg_insert(ArtifactRepository)
        .values(
            artifact_id=artifact_id,
            repository_github_id=repository_github_id,
            full_name=full_name,
        )
        .on_conflict_do_update(
            index_elements=[ArtifactRepository.artifact_id],
            set_={
                "repository_github_id": repository_github_id,
                "full_name": full_name,
            },
        )
    )
    session.execute(stmt)


def upsert_artifact_changeset(
    session: Session,
    *,
    artifact_id: uuid.UUID,
    repository_github_id: int,
    number: int,
    head_sha: str | None,
    repo_full_name: str | None,
) -> None:
    stmt = (
        pg_insert(ArtifactChangeset)
        .values(
            artifact_id=artifact_id,
            repository_github_id=repository_github_id,
            number=number,
            head_sha=head_sha,
            repo_full_name=repo_full_name,
        )
        .on_conflict_do_update(
            index_elements=[ArtifactChangeset.artifact_id],
            set_={
                "repository_github_id": repository_github_id,
                "number": number,
                "head_sha": head_sha,
                "repo_full_name": repo_full_name,
            },
        )
    )
    session.execute(stmt)


def upsert_artifact_revision(
    session: Session,
    *,
    artifact_id: uuid.UUID,
    repository_github_id: int,
    sha: str,
    repo_full_name: str | None,
) -> None:
    stmt = (
        pg_insert(ArtifactRevision)
        .values(
            artifact_id=artifact_id,
            repository_github_id=repository_github_id,
            sha=sha,
            repo_full_name=repo_full_name,
        )
        .on_conflict_do_update(
            index_elements=[ArtifactRevision.artifact_id],
            set_={
                "repository_github_id": repository_github_id,
                "sha": sha,
                "repo_full_name": repo_full_name,
            },
        )
    )
    session.execute(stmt)


def upsert_artifact_trackable_unit(
    session: Session,
    *,
    artifact_id: uuid.UUID,
    provider: str,
    key: str | None,
    url: str | None,
    repository_github_id: int | None,
    issue_number: int | None,
) -> None:
    stmt = (
        pg_insert(ArtifactTrackableUnit)
        .values(
            artifact_id=artifact_id,
            provider=provider,
            key=key,
            url=url,
            repository_github_id=repository_github_id,
            issue_number=issue_number,
        )
        .on_conflict_do_update(
            index_elements=[ArtifactTrackableUnit.artifact_id],
            set_={
                "provider": provider,
                "key": key,
                "url": url,
                "repository_github_id": repository_github_id,
                "issue_number": issue_number,
            },
        )
    )
    session.execute(stmt)


def upsert_relationship(
    session: Session,
    *,
    id: uuid.UUID,
    tenant_id: uuid.UUID,
    subject_type: str,
    subject_id: uuid.UUID,
    object_type: str,
    object_id: uuid.UUID,
    relation_kind_id: int,
    source: str,
    confidence: float | None,
    evidence_ref: str | None,
    rule_version: str | None,
    rule_source: str | None,
    valid_from: datetime,
    valid_to: datetime | None,
) -> None:
    stmt = (
        pg_insert(Relationship)
        .values(
            id=id,
            tenant_id=tenant_id,
            subject_type=subject_type,
            subject_id=subject_id,
            object_type=object_type,
            object_id=object_id,
            relation_kind_id=relation_kind_id,
            source=source,
            confidence=confidence,
            evidence_ref=evidence_ref,
            rule_version=rule_version,
            rule_source=rule_source,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        .on_conflict_do_update(
            index_elements=[Relationship.id],
            set_={
                "tenant_id": tenant_id,
                "subject_type": subject_type,
                "subject_id": subject_id,
                "object_type": object_type,
                "object_id": object_id,
                "relation_kind_id": relation_kind_id,
                "source": source,
                "confidence": confidence,
                "evidence_ref": evidence_ref,
                "rule_version": rule_version,
                "rule_source": rule_source,
                "valid_from": valid_from,
                "valid_to": valid_to,
            },
        )
    )
    session.execute(stmt)
