"""Step 3 canonical ontology ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class ArtifactKind(Base):
    __tablename__ = "artifact_kind"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_container: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RelationKind(Base):
    __tablename__ = "relation_kind"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject_kind: Mapped[str] = mapped_column(Text, nullable=False)
    object_kind: Mapped[str] = mapped_column(Text, nullable=False)


class Actor(Base):
    __tablename__ = "actor"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False, default="person")
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ActorExternalIdentity(Base):
    __tablename__ = "actor_external_identity"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("actor.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connector: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    traits_json: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class Artifact(Base):
    __tablename__ = "artifact"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_kind_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("artifact_kind.id"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class ArtifactRepository(Base):
    __tablename__ = "artifact_repository"

    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact.id", ondelete="CASCADE"),
        primary_key=True,
    )
    repository_github_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)


class ArtifactTrackableUnit(Base):
    __tablename__ = "artifact_trackable_unit"

    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact.id", ondelete="CASCADE"),
        primary_key=True,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False, default="github")
    key: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    repository_github_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    issue_number: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ArtifactChangeset(Base):
    __tablename__ = "artifact_changeset"

    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact.id", ondelete="CASCADE"),
        primary_key=True,
    )
    repository_github_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    head_sha: Mapped[str | None] = mapped_column(Text, nullable=True)
    repo_full_name: Mapped[str | None] = mapped_column(Text, nullable=True)


class ArtifactRevision(Base):
    __tablename__ = "artifact_revision"

    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact.id", ondelete="CASCADE"),
        primary_key=True,
    )
    repository_github_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha: Mapped[str] = mapped_column(Text, nullable=False)
    repo_full_name: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExternalReference(Base):
    __tablename__ = "external_reference"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    connector: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_key: Mapped[str] = mapped_column(Text, nullable=False)
    connection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_raw_record_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class MappingEvent(Base):
    __tablename__ = "mapping_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("external_reference.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("actor.id", ondelete="SET NULL"),
        nullable=True,
    )
    rule_version: Mapped[str] = mapped_column(Text, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    supersedes_event_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class CurrentMapping(Base):
    __tablename__ = "current_mapping"

    external_reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("external_reference.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifact.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("actor.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Relationship(Base):
    __tablename__ = "relationship"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_type: Mapped[str] = mapped_column(Text, nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    object_type: Mapped[str] = mapped_column(Text, nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relation_kind_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("relation_kind.id"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Step3CanonicalCursor(Base):
    __tablename__ = "step3_canonical_cursor"

    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    connector: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    last_replay_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_raw_record_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
