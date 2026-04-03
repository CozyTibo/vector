"""Ingestion pipeline tasks (thin wrappers — domain logic stays in `vector.domains`)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from vector.application.services import ingestion_sweep
from vector.application.services.connector_sync import (
    run_github_execute_poll_run_inline,
    run_linear_execute_poll_run_inline,
)
from vector.domains.canonical.worker import drain_github_canonical, drain_linear_canonical
from vector.domains.projections.github.worker import drain_github_projections
from vector.domains.projections.linear.worker import drain_linear_projections
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.repositories import ingestion as ing_repo
from vector.infrastructure.db.session import session_scope
from vector.infrastructure.observability.ingestion_tasks import (
    PHASE_STEP1,
    PHASE_SWEEP,
    log_ingestion_event,
)
from vector.settings import get_settings

_logger = logging.getLogger(__name__)

_TASK_GITHUB = "vector.ingestion.github_execute_poll_run"
_TASK_LINEAR = "vector.ingestion.linear_execute_poll_run"
_TASK_SWEEP = "vector.ingestion.sweep_canonical_lag"


@celery_app.task(name=_TASK_GITHUB)
def github_execute_poll_run(run_id: str) -> dict[str, str | None]:
    """Step 1 GitHub poll for an existing `ingestion_runs` row, then Step 2 + Step 3 drains."""
    rid = uuid.UUID(run_id)
    settings = get_settings()
    for session in session_scope():
        run = session.get(IngestionRun, rid)
        if run is None:
            msg = (
                f"ingestion run not found: run_id={rid} task={_TASK_GITHUB} phase={PHASE_STEP1}"
            )
            raise ValueError(msg)

        base = {
            "run_id": str(run.id),
            "tenant_id": str(run.tenant_id),
            "connector": run.connector,
        }

        if run.connector != ing_repo.CONNECTOR_GITHUB:
            msg = (
                f"ingestion run connector mismatch: run_id={run.id} "
                f"tenant_id={run.tenant_id} expected={ing_repo.CONNECTOR_GITHUB!r} "
                f"got={run.connector!r} task={_TASK_GITHUB} phase={PHASE_STEP1}"
            )
            raise ValueError(msg)

        if run.status == ing_repo.RUN_STATUS_SUCCEEDED:
            _drain_github_after_step1(session, run)
            log_ingestion_event(
                _logger,
                logging.INFO,
                "ingestion task replay drains after prior step1 success",
                task_name=_TASK_GITHUB,
                phase=PHASE_STEP1,
                outcome="replay_drains",
                run_status=run.status,
                **base,
            )
            return {"status": "ok", "run_status": run.status}

        if run.status != ing_repo.RUN_STATUS_RUNNING:
            msg = (
                f"ingestion run not runnable: run_id={run.id} tenant_id={run.tenant_id} "
                f"status={run.status!r} task={_TASK_GITHUB} phase={PHASE_STEP1}"
            )
            raise ValueError(msg)

        run = run_github_execute_poll_run_inline(session, settings, run)
        if run.status != ing_repo.RUN_STATUS_SUCCEEDED:
            msg = (
                f"GitHub ingestion finished unsuccessfully: run_id={run.id} "
                f"tenant_id={run.tenant_id} status={run.status!r} "
                f"task={_TASK_GITHUB} phase={PHASE_STEP1}"
            )
            raise RuntimeError(msg)

        log_ingestion_event(
            _logger,
            logging.INFO,
            "ingestion task finished",
            task_name=_TASK_GITHUB,
            phase=PHASE_STEP1,
            outcome="success",
            run_status=run.status,
            **base,
        )
        return {"status": "ok", "run_status": run.status}

    msg = f"ingestion task: session_scope did not yield a session task={_TASK_GITHUB}"
    raise RuntimeError(msg)


@celery_app.task(name=_TASK_LINEAR)
def linear_execute_poll_run(run_id: str) -> dict[str, str | None]:
    """Step 1 Linear GraphQL for an existing run, then Step 2 + Step 3 drains."""
    rid = uuid.UUID(run_id)
    settings = get_settings()
    for session in session_scope():
        run = session.get(IngestionRun, rid)
        if run is None:
            msg = (
                f"ingestion run not found: run_id={rid} task={_TASK_LINEAR} phase={PHASE_STEP1}"
            )
            raise ValueError(msg)

        base = {
            "run_id": str(run.id),
            "tenant_id": str(run.tenant_id),
            "connector": run.connector,
        }

        if run.connector != ing_repo.CONNECTOR_LINEAR:
            msg = (
                f"ingestion run connector mismatch: run_id={run.id} "
                f"tenant_id={run.tenant_id} expected={ing_repo.CONNECTOR_LINEAR!r} "
                f"got={run.connector!r} task={_TASK_LINEAR} phase={PHASE_STEP1}"
            )
            raise ValueError(msg)

        if run.status == ing_repo.RUN_STATUS_SUCCEEDED:
            _drain_linear_after_step1(session, run)
            log_ingestion_event(
                _logger,
                logging.INFO,
                "ingestion task replay drains after prior step1 success",
                task_name=_TASK_LINEAR,
                phase=PHASE_STEP1,
                outcome="replay_drains",
                run_status=run.status,
                **base,
            )
            return {"status": "ok", "run_status": run.status}

        if run.status != ing_repo.RUN_STATUS_RUNNING:
            msg = (
                f"ingestion run not runnable: run_id={run.id} tenant_id={run.tenant_id} "
                f"status={run.status!r} task={_TASK_LINEAR} phase={PHASE_STEP1}"
            )
            raise ValueError(msg)

        run = run_linear_execute_poll_run_inline(session, settings, run)
        if run.status != ing_repo.RUN_STATUS_SUCCEEDED:
            msg = (
                f"Linear ingestion finished unsuccessfully: run_id={run.id} "
                f"tenant_id={run.tenant_id} status={run.status!r} "
                f"task={_TASK_LINEAR} phase={PHASE_STEP1}"
            )
            raise RuntimeError(msg)

        log_ingestion_event(
            _logger,
            logging.INFO,
            "ingestion task finished",
            task_name=_TASK_LINEAR,
            phase=PHASE_STEP1,
            outcome="success",
            run_status=run.status,
            **base,
        )
        return {"status": "ok", "run_status": run.status}

    msg = f"ingestion task: session_scope did not yield a session task={_TASK_LINEAR}"
    raise RuntimeError(msg)


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


def _drain_linear_after_step1(session: Session, run: IngestionRun) -> None:
    drain_linear_projections(
        session,
        tenant_id=run.tenant_id,
        connection_id=run.connection_id,
    )
    drain_linear_canonical(
        session,
        tenant_id=run.tenant_id,
        connection_id=run.connection_id,
    )


@celery_app.task(name="vector.ingestion.health_ping")
def health_ping() -> str:
    """Verify broker + worker wiring."""
    return "pong"


@celery_app.task(name=_TASK_SWEEP)
def sweep_canonical_lag() -> dict[str, int | str]:
    """Repair Step 2/3 backlog for connections where Step 3 lags Step 2."""
    for session in session_scope():
        out = ingestion_sweep.sweep_canonical_lag_once(session)
        log_ingestion_event(
            _logger,
            logging.INFO,
            "canonical lag sweep finished",
            task_name=_TASK_SWEEP,
            phase=PHASE_SWEEP,
            outcome="success",
            connections_seen=out["connections_seen"],
            connections_swept=out["connections_swept"],
            canonical_rows_processed=out["canonical_rows_processed"],
        )
        return out
    msg = f"canonical lag sweep: session_scope did not yield a session task={_TASK_SWEEP}"
    raise RuntimeError(msg)
