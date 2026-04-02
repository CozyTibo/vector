"""Delete Step 2 (projections) or Step 3 (canonical) data for a tenant — no connector I/O."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from vector.domains.debug.github_pipeline_wipe import _delete_step3_canonical_entities_for_tenant
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
from vector.infrastructure.db.models.github_projection import (
    GithubCommit,
    GithubIssue,
    GithubPullRequest,
    GithubRepository,
    GithubUser,
)
from vector.infrastructure.db.models.linear_projection import (
    LinearIssue,
    LinearIssueComment,
    LinearProject,
    LinearTeam,
    LinearUser,
)

# Typed in the admin UI before reset runs (must match exactly, case-sensitive).
STEP2_PROJECTIONS_RESET_CONFIRMATION_PHRASE = "DELETE ALL STEP2 PROJECTION DATA"
STEP3_CANONICAL_RESET_CONFIRMATION_PHRASE = "DELETE ALL STEP3 CANONICAL DATA"


def _count_where(session: Session, model: type, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(model).where(model.tenant_id == tenant_id),
        )
        or 0,
    )


def wipe_step2_projections_for_tenant(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    """Remove all connector projection tables and projection cursors for the tenant.

    Does not touch Step 1 raw rows or Step 3 canonical tables.
    """
    github_models = (
        GithubCommit,
        GithubIssue,
        GithubPullRequest,
        GithubRepository,
        GithubUser,
    )
    linear_models = (LinearUser, LinearTeam, LinearProject, LinearIssue, LinearIssueComment)

    n_github = sum(_count_where(session, m, tenant_id) for m in github_models)
    n_linear = sum(_count_where(session, m, tenant_id) for m in linear_models)
    n_prog = int(
        session.scalar(
            select(func.count())
            .select_from(ConnectorProjectionProgress)
            .where(ConnectorProjectionProgress.tenant_id == tenant_id),
        )
        or 0,
    )

    for m in github_models:
        session.execute(delete(m).where(m.tenant_id == tenant_id))
    for m in linear_models:
        session.execute(delete(m).where(m.tenant_id == tenant_id))
    session.execute(
        delete(ConnectorProjectionProgress).where(
            ConnectorProjectionProgress.tenant_id == tenant_id,
        ),
    )

    return {
        "deleted_github_projection_rows": n_github,
        "deleted_linear_projection_rows": n_linear,
        "deleted_connector_projection_progress_rows": n_prog,
    }


def wipe_step3_canonical_for_tenant(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    """Remove all Step 3 canonical ontology rows and drain cursors for the tenant.

    Does not touch Step 1 or Step 2.
    """
    n_rel = _count_where(session, Relationship, tenant_id)
    n_me = _count_where(session, MappingEvent, tenant_id)
    n_cm = _count_where(session, CurrentMapping, tenant_id)
    n_xr = _count_where(session, ExternalReference, tenant_id)
    n_aei = _count_where(session, ActorExternalIdentity, tenant_id)
    n_art = _count_where(session, Artifact, tenant_id)
    n_act = _count_where(session, Actor, tenant_id)
    n_cur = int(
        session.scalar(
            select(func.count())
            .select_from(Step3CanonicalCursor)
            .where(Step3CanonicalCursor.tenant_id == tenant_id),
        )
        or 0,
    )

    _delete_step3_canonical_entities_for_tenant(session, tenant_id=tenant_id)
    session.execute(delete(Step3CanonicalCursor).where(Step3CanonicalCursor.tenant_id == tenant_id))

    return {
        "deleted_relationships": n_rel,
        "deleted_mapping_events": n_me,
        "deleted_current_mappings": n_cm,
        "deleted_external_references": n_xr,
        "deleted_actor_external_identities": n_aei,
        "deleted_artifacts": n_art,
        "deleted_actors": n_act,
        "deleted_step3_canonical_cursors": n_cur,
    }
