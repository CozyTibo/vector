"""Shared GitHub pipeline wipe helpers (Step 1–3) for debug + admin routes."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from vector.domains.canonical.worker import drain_github_canonical
from vector.domains.projections.github.worker import drain_github_projections
from vector.infrastructure.db.models.canonical import (
    Actor,
    ActorExternalIdentity,
    Artifact,
    CurrentMapping,
    ExternalReference,
    MappingEvent,
    Relationship,
    Step3CanonicalCursor,
)
from vector.infrastructure.db.models.connector_projection_progress import (
    ConnectorProjectionProgress,
)
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.github_projection import (
    GithubCommit,
    GithubIssue,
    GithubPullRequest,
    GithubRepository,
    GithubUser,
)
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_GITHUB


def _delete_step3_canonical_entities_for_tenant(
    db: Session,
    *,
    tenant_id: uuid.UUID,
) -> None:
    """Remove ontology rows for a tenant (not Step3 cursors). Order respects FKs."""
    db.execute(delete(Relationship).where(Relationship.tenant_id == tenant_id))
    db.execute(delete(MappingEvent).where(MappingEvent.tenant_id == tenant_id))
    db.execute(delete(CurrentMapping).where(CurrentMapping.tenant_id == tenant_id))
    db.execute(delete(ExternalReference).where(ExternalReference.tenant_id == tenant_id))
    db.execute(
        delete(ActorExternalIdentity).where(ActorExternalIdentity.tenant_id == tenant_id),
    )
    db.execute(delete(Artifact).where(Artifact.tenant_id == tenant_id))
    db.execute(delete(Actor).where(Actor.tenant_id == tenant_id))


def wipe_step3_canonical_for_tenant_connection(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> None:
    _delete_step3_canonical_entities_for_tenant(db, tenant_id=tenant_id)
    db.execute(
        delete(Step3CanonicalCursor).where(
            Step3CanonicalCursor.tenant_id == tenant_id,
            Step3CanonicalCursor.connection_id == connection_id,
            Step3CanonicalCursor.connector == CONNECTOR_GITHUB,
        ),
    )


def wipe_step2_github_projections_for_connection(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> None:
    db.execute(
        delete(GithubCommit).where(
            GithubCommit.tenant_id == tenant_id,
            GithubCommit.connection_id == connection_id,
        ),
    )
    db.execute(
        delete(GithubIssue).where(
            GithubIssue.tenant_id == tenant_id,
            GithubIssue.connection_id == connection_id,
        ),
    )
    db.execute(
        delete(GithubPullRequest).where(
            GithubPullRequest.tenant_id == tenant_id,
            GithubPullRequest.connection_id == connection_id,
        ),
    )
    db.execute(
        delete(GithubRepository).where(
            GithubRepository.tenant_id == tenant_id,
            GithubRepository.connection_id == connection_id,
        ),
    )
    db.execute(
        delete(GithubUser).where(
            GithubUser.tenant_id == tenant_id,
            GithubUser.connection_id == connection_id,
        ),
    )
    db.execute(
        delete(ConnectorProjectionProgress).where(
            ConnectorProjectionProgress.tenant_id == tenant_id,
            ConnectorProjectionProgress.connection_id == connection_id,
            ConnectorProjectionProgress.connector == CONNECTOR_GITHUB,
        ),
    )


def wipe_step1_github_ingestion_for_connection(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> None:
    db.execute(
        delete(IngestionRun).where(
            IngestionRun.tenant_id == tenant_id,
            IngestionRun.connection_id == connection_id,
            IngestionRun.connector == CONNECTOR_GITHUB,
        ),
    )
    db.execute(
        delete(ConnectorSyncState).where(
            ConnectorSyncState.tenant_id == tenant_id,
            ConnectorSyncState.connection_id == connection_id,
            ConnectorSyncState.connector == CONNECTOR_GITHUB,
        ),
    )


def reset_github_pipeline_state(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> None:
    """Nuclear reset: Step 3 + Step 2 + Step 1 (raw runs + sync watermarks)."""
    wipe_step3_canonical_for_tenant_connection(
        db,
        tenant_id=tenant_id,
        connection_id=connection_id,
    )
    wipe_step2_github_projections_for_connection(
        db,
        tenant_id=tenant_id,
        connection_id=connection_id,
    )
    wipe_step1_github_ingestion_for_connection(
        db,
        tenant_id=tenant_id,
        connection_id=connection_id,
    )
    db.commit()


def rebuild_derived_from_step1_github(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> tuple[Any, Any]:
    """Keep raw rows; wipe Step 3 + Step 2; replay projection + canonical."""
    wipe_step3_canonical_for_tenant_connection(
        db,
        tenant_id=tenant_id,
        connection_id=connection_id,
    )
    wipe_step2_github_projections_for_connection(
        db,
        tenant_id=tenant_id,
        connection_id=connection_id,
    )
    db.commit()
    p = drain_github_projections(
        db,
        tenant_id=tenant_id,
        connection_id=connection_id,
    )
    c = drain_github_canonical(
        db,
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR_GITHUB,
    )
    return p, c
