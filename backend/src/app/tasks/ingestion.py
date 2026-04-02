"""Ingestion pipeline tasks (thin wrappers — domain logic stays in `vector.domains`)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.celery_app import app
from vector.application.services.connector_sync import run_github_execute_poll_run_inline
from vector.domains.canonical.worker import drain_github_canonical
from vector.domains.projections.github.worker import drain_github_projections
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.repositories import ingestion as ing_repo
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_logger = logging.getLogger(__name__)


@app.task(name="vector.ingestion.health_ping")
def health_ping() -> str:
    """Verify broker + worker wiring."""
    return "pong"


@app.task(name="vector.ingestion.github_execute_poll_run")
def github_execute_poll_run(run_id: str) -> dict[str, str | None]:
    """Step 1 GitHub poll for an existing `ingestion_runs` row, then Step 2 + Step 3 drains."""
    rid = uuid.UUID(run_id)
    settings = get_settings()
    for session in session_scope():
        run = session.get(IngestionRun, rid)
        if run is None:
            _logger.warning("github_execute_poll_run: run not found %s", run_id)
            return {"status": "missing_run"}

        if run.connector != ing_repo.CONNECTOR_GITHUB:
            _logger.warning(
                "github_execute_poll_run: wrong connector %s for run %s",
                run.connector,
                run_id,
            )
            return {"status": "wrong_connector"}

        # Idempotent: replay drains if Step 1 already finished (e.g. retry after success).
        if run.status == ing_repo.RUN_STATUS_SUCCEEDED:
            _drain_github_after_step1(session, run)
            return {"status": "ok", "run_status": run.status}

        if run.status != ing_repo.RUN_STATUS_RUNNING:
            return {"status": "skipped", "run_status": run.status}

        run = run_github_execute_poll_run_inline(session, settings, run)
        return {"status": "ok", "run_status": run.status}


def _drain_github_after_step1(session: Session, run: IngestionRun) -> None:
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
