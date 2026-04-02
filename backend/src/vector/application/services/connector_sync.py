"""Orchestrate connector ingestion (HTTP + workers call into this layer)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.domains.ingestion.github_poll_sync import (
    execute_github_poll_ingestion_run,
    run_github_poll_ingestion_for_tenant,
)
from vector.domains.ingestion.http_fetch import FetchFatalError
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.infrastructure.db.repositories import ingestion as ing_repo
from vector.settings import Settings


def enqueue_github_poll_sync(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> IngestionRun:
    """Create a GitHub ingestion run and queue Step 1 (+ drains) on the worker.

    Caller must commit the session after this returns so the run is visible to the worker.
    """
    from app.tasks.ingestion import github_execute_poll_run

    link = gh_repo.get_github_connection_for_tenant(session, tenant_id)
    if link is None:
        msg = "GitHub is not connected for this tenant"
        raise FetchFatalError(msg)

    run = ing_repo.create_ingestion_run(
        session,
        tenant_id=tenant_id,
        connection_id=link.connection.id,
        connector=ing_repo.CONNECTOR_GITHUB,
        source_trigger=ing_repo.SOURCE_TRIGGER_POLL,
    )
    session.flush()
    github_execute_poll_run.delay(str(run.id))
    return run


def run_github_poll_sync_with_drains(
    session: Session,
    settings: Settings,
    tenant_id: uuid.UUID,
) -> IngestionRun:
    """Step 1 + projection + canonical in-process (legacy synchronous pipeline)."""
    from vector.domains.canonical.worker import drain_github_canonical
    from vector.domains.projections.github.worker import drain_github_projections

    run = run_github_poll_ingestion_for_tenant(session, settings, tenant_id)
    if run.status == ing_repo.RUN_STATUS_SUCCEEDED:
        drain_github_projections(
            session,
            tenant_id=tenant_id,
            connection_id=run.connection_id,
        )
        drain_github_canonical(
            session,
            tenant_id=tenant_id,
            connection_id=run.connection_id,
        )
    return run


def run_github_execute_poll_run_inline(
    session: Session,
    settings: Settings,
    run: IngestionRun,
) -> IngestionRun:
    """Execute Step 1 for an existing run, then projection + canonical (admin/worker parity)."""
    from vector.domains.canonical.worker import drain_github_canonical
    from vector.domains.projections.github.worker import drain_github_projections

    run = execute_github_poll_ingestion_run(session, settings, run)
    if run.status == ing_repo.RUN_STATUS_SUCCEEDED:
        drain_github_projections(
            session,
            tenant_id=run.tenant_id,
            connection_id=run.connection_id,
        )
        drain_github_canonical(
            session,
            tenant_id=run.tenant_id,
            connection_id=run.connection_id,
        )
    return run
