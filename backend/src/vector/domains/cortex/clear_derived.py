"""Clear tenant Cortex derived state while preserving raw ingestion rows."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from vector.domains.cortex.runtime.pass_types import (
    ACTIVE_STATUSES,
    CANON_PASS,
    STATUS_CANCELLED,
)
from vector.domains.cortex.runtime.queue import upsert_pending_pass_v1
from vector.infrastructure.db.models.canon_dirty_queue import CanonDirtyQueue
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_materialization_cursor import CanonMaterializationCursor
from vector.infrastructure.db.models.canon_pass_run import CanonPassRun
from vector.infrastructure.db.models.cortex_admin_continuity_snapshot import CortexAdminContinuitySnapshot
from vector.infrastructure.db.models.cortex_admin_graph_component_snapshot import (
    CortexAdminGraphComponentSnapshot,
)
from vector.infrastructure.db.models.cortex_pass import CortexPass
from vector.infrastructure.db.models.declared_domain import DeclaredDomain
from vector.infrastructure.db.models.declared_domain_dirty_queue import DeclaredDomainDirtyQueue
from vector.infrastructure.db.models.declared_domain_membership import DeclaredDomainMembership
from vector.infrastructure.db.models.declared_domain_pass_run import DeclaredDomainPassRun
from vector.infrastructure.db.models.declared_domain_stats import DeclaredDomainStats
from vector.infrastructure.db.models.graph_dirty_queue import GraphDirtyQueue
from vector.infrastructure.db.models.graph_pass_run import GraphPassRun
from vector.infrastructure.db.models.graph_relationship import GraphRelationship
from vector.infrastructure.db.models.graph_unresolved_reference import GraphUnresolvedReference
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_dirty_queue import IdentityDirtyQueue
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.identity_pass_run import IdentityPassRun
from vector.infrastructure.db.models.identity_suggestion import IdentitySuggestion
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_archive_catalog import RawMemoryArchiveCatalog
from vector.infrastructure.db.models.raw_memory_failure_case import RawMemoryFailureCase
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex
from vector.infrastructure.db.models.raw_memory_recovery_validation import RawMemoryRecoveryValidation
from vector.infrastructure.db.models.raw_memory_retention_event import RawMemoryRetentionEvent
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex
from vector.infrastructure.db.models.raw_memory_trust_state import RawMemoryTrustState
from vector.infrastructure.db.models.raw_memory_trust_transition import RawMemoryTrustTransition
from vector.infrastructure.db.session import session_scope

CLEAR_DERIVED_CORTEX_CONFIRMATION_PHRASE = "CLEAR DERIVED CORTEX EXECUTION OUTPUTS"
_DEADLOCK_MAX_ATTEMPTS = 5
_RELATIONSHIP_DELETE_BATCH = 2_000
_CANON_ENTITY_DELETE_BATCH = 2_000

_logger = logging.getLogger(__name__)


def _delete_count(session: Session, stmt) -> int:
    result = session.execute(stmt)
    return int(result.rowcount or 0)


def _is_deadlock(exc: BaseException) -> bool:
    if isinstance(exc, OperationalError):
        orig = getattr(exc, "orig", None)
        if orig is not None and orig.__class__.__name__ == "DeadlockDetected":
            return True
    return "deadlock" in str(exc).lower()


def _delete_where_tenant_batched(
    session: Session,
    table: type,
    *,
    tenant_id: uuid.UUID,
    batch_size: int,
) -> int:
    total = 0
    while True:
        ids = list(
            session.scalars(
                select(table.id).where(table.tenant_id == tenant_id).limit(batch_size),
            ).all(),
        )
        if not ids:
            break
        total += _delete_count(session, delete(table).where(table.id.in_(ids)))
        session.flush()
    return total


def _cancel_active_passes_for_tenant(session: Session, *, tenant_id: uuid.UUID) -> int:
    return _delete_count(
        session,
        update(CortexPass)
        .where(
            CortexPass.tenant_id == tenant_id,
            CortexPass.status.in_(tuple(sorted(ACTIVE_STATUSES))),
        )
        .values(
            status=STATUS_CANCELLED,
            locked_by=None,
            locked_until=None,
        ),
    )


def _clear_declared_domains(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    deleted: dict[str, int] = {}

    def _del(table: type, name: str) -> None:
        deleted[name] = _delete_count(session, delete(table).where(table.tenant_id == tenant_id))

    _del(DeclaredDomainMembership, "declared_domain_memberships")
    _del(DeclaredDomainStats, "declared_domain_stats")
    _del(DeclaredDomain, "declared_domains")
    _del(DeclaredDomainDirtyQueue, "declared_domain_dirty_queue")
    _del(DeclaredDomainPassRun, "declared_domain_pass_runs")
    return deleted


def _clear_graph(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    cancelled = _cancel_active_passes_for_tenant(session, tenant_id=tenant_id)
    out = {
        "graph_relationships": _delete_where_tenant_batched(
            session,
            GraphRelationship,
            tenant_id=tenant_id,
            batch_size=_RELATIONSHIP_DELETE_BATCH,
        ),
        "graph_unresolved_references": _delete_count(
            session,
            delete(GraphUnresolvedReference).where(GraphUnresolvedReference.tenant_id == tenant_id),
        ),
        "graph_dirty_queue": _delete_count(
            session,
            delete(GraphDirtyQueue).where(GraphDirtyQueue.tenant_id == tenant_id),
        ),
        "graph_pass_runs": _delete_count(
            session,
            delete(GraphPassRun).where(GraphPassRun.tenant_id == tenant_id),
        ),
    }
    if cancelled:
        out["cortex_passes_cancelled_before_graph"] = cancelled
    return out


def _clear_identity(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    deleted: dict[str, int] = {}

    def _del(table: type, name: str) -> None:
        deleted[name] = _delete_count(session, delete(table).where(table.tenant_id == tenant_id))

    _del(IdentitySuggestion, "identity_suggestions")
    _del(IdentityAccount, "identity_accounts")
    _del(IdentityEntity, "identity_entities")
    _del(IdentityDirtyQueue, "identity_dirty_queue")
    _del(IdentityPassRun, "identity_pass_runs")
    return deleted


def _clear_canon(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    cancelled = _cancel_active_passes_for_tenant(session, tenant_id=tenant_id)
    out = {
        "canon_entities": _delete_where_tenant_batched(
            session,
            CanonEntity,
            tenant_id=tenant_id,
            batch_size=_CANON_ENTITY_DELETE_BATCH,
        ),
        "canon_dirty_queue": _delete_count(
            session,
            delete(CanonDirtyQueue).where(CanonDirtyQueue.tenant_id == tenant_id),
        ),
        "canon_pass_runs": _delete_count(
            session,
            delete(CanonPassRun).where(CanonPassRun.tenant_id == tenant_id),
        ),
        "canon_materialization_cursors": _delete_count(
            session,
            delete(CanonMaterializationCursor).where(CanonMaterializationCursor.tenant_id == tenant_id),
        ),
    }
    if cancelled:
        out["cortex_passes_cancelled_before_canon"] = cancelled
    return out


def _clear_passes_and_admin_snapshots(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    return {
        "cortex_passes": _delete_count(
            session,
            delete(CortexPass).where(CortexPass.tenant_id == tenant_id),
        ),
        "cortex_admin_continuity_snapshot": _delete_count(
            session,
            delete(CortexAdminContinuitySnapshot).where(
                CortexAdminContinuitySnapshot.tenant_id == tenant_id,
            ),
        ),
        "cortex_admin_graph_component_snapshot": _delete_count(
            session,
            delete(CortexAdminGraphComponentSnapshot).where(
                CortexAdminGraphComponentSnapshot.tenant_id == tenant_id,
            ),
        ),
    }


def _clear_raw_memory_indexes(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    deleted: dict[str, int] = {}

    def _del(table: type, name: str) -> None:
        deleted[name] = _delete_count(session, delete(table).where(table.tenant_id == tenant_id))

    _del(RawMemoryLineageIndex, "raw_memory_lineage_index")
    _del(RawMemoryRevisionIndex, "raw_memory_revision_index")
    _del(RawMemoryArchiveCatalog, "raw_memory_archive_catalog")
    _del(RawMemoryFailureCase, "raw_memory_failure_cases")
    _del(RawMemoryRecoveryValidation, "raw_memory_recovery_validations")
    _del(RawMemoryTrustState, "raw_memory_trust_state")
    _del(RawMemoryTrustTransition, "raw_memory_trust_transitions")
    _del(RawMemoryRetentionEvent, "raw_memory_retention_events")
    return deleted


_CLEAR_STEPS: list[tuple[str, Callable[[Session, uuid.UUID], dict[str, int]]]] = [
    ("cancel_active_passes", lambda s, tid: {"cortex_passes_cancelled": _cancel_active_passes_for_tenant(s, tenant_id=tid)}),
    ("declared_domains", lambda s, tid: _clear_declared_domains(s, tenant_id=tid)),
    ("graph", lambda s, tid: _clear_graph(s, tenant_id=tid)),
    ("identity", lambda s, tid: _clear_identity(s, tenant_id=tid)),
    ("canon", lambda s, tid: _clear_canon(s, tenant_id=tid)),
    ("passes_and_snapshots", lambda s, tid: _clear_passes_and_admin_snapshots(s, tenant_id=tid)),
    ("raw_memory_indexes", lambda s, tid: _clear_raw_memory_indexes(s, tenant_id=tid)),
]


def _run_step_with_deadlock_retry(
    step_name: str,
    step_fn: Callable[[Session, uuid.UUID], dict[str, int]],
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    for attempt in range(1, _DEADLOCK_MAX_ATTEMPTS + 1):
        try:
            with session_scope() as session:
                counts = step_fn(session, tenant_id)
            _logger.info(
                "clear_derived step completed",
                extra={"tenant_id": str(tenant_id), "step": step_name, "counts": counts},
            )
            return counts
        except OperationalError as exc:
            if not _is_deadlock(exc) or attempt >= _DEADLOCK_MAX_ATTEMPTS:
                raise
            delay_s = 0.5 * attempt
            _logger.warning(
                "clear_derived step deadlock; retrying",
                extra={
                    "tenant_id": str(tenant_id),
                    "step": step_name,
                    "attempt": attempt,
                    "delay_s": delay_s,
                },
            )
            time.sleep(delay_s)
    msg = f"unreachable_clear_derived_step:{step_name}"
    raise RuntimeError(msg)


def execute_clear_derived_cortex_for_tenant(*, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Delete derived substrate in committed phases to avoid long transactions and deadlocks."""
    deleted: dict[str, int] = {}
    for step_name, step_fn in _CLEAR_STEPS:
        deleted.update(_run_step_with_deadlock_retry(step_name, step_fn, tenant_id=tenant_id))

    with session_scope() as session:
        raw_rows_remaining = int(
            session.scalar(
                select(func.count())
                .select_from(RawIngestionRecord)
                .where(
                    RawIngestionRecord.tenant_id == tenant_id,
                    RawIngestionRecord.replay_job_id.is_(None),
                ),
            )
            or 0,
        )

    return {
        "tenant_id": tenant_id,
        "deleted_rows_by_table": deleted,
        "deleted_rows_total": sum(deleted.values()),
        "raw_ingestion_rows_remaining": raw_rows_remaining,
    }


def clear_derived_cortex_for_tenant(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Single-session clear (tests); production uses ``execute_clear_derived_cortex_for_tenant``."""
    deleted: dict[str, int] = {}
    for _step_name, step_fn in _CLEAR_STEPS:
        deleted.update(step_fn(session, tenant_id))
    raw_rows_remaining = int(
        session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
            ),
        )
        or 0,
    )
    return {
        "tenant_id": tenant_id,
        "deleted_rows_by_table": deleted,
        "deleted_rows_total": sum(deleted.values()),
        "raw_ingestion_rows_remaining": raw_rows_remaining,
    }


def enqueue_cortex_rematerialization_after_clear(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> uuid.UUID:
    """Schedule canon pass from raw cursor zero; downstream lanes follow via materialize + scheduler."""
    return upsert_pending_pass_v1(
        session,
        tenant_id=tenant_id,
        pass_type=CANON_PASS,
        source_trigger="clear_derived_admin",
        priority=100,
    )
