"""Clear tenant Cortex derived state while preserving raw ingestion rows."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.runtime.pass_types import CANON_PASS
from vector.domains.cortex.runtime.queue import upsert_pending_pass_v1
from vector.infrastructure.db.models.canon_dirty_queue import CanonDirtyQueue
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_materialization_cursor import CanonMaterializationCursor
from vector.infrastructure.db.models.canon_pass_run import CanonPassRun
from vector.infrastructure.db.models.canon_scheduler_tick import CanonSchedulerTick
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
from vector.infrastructure.db.models.graph_scheduler_tick import GraphSchedulerTick
from vector.infrastructure.db.models.graph_unresolved_reference import GraphUnresolvedReference
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_dirty_queue import IdentityDirtyQueue
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.identity_pass_run import IdentityPassRun
from vector.infrastructure.db.models.identity_scheduler_tick import IdentitySchedulerTick
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

CLEAR_DERIVED_CORTEX_CONFIRMATION_PHRASE = "CLEAR DERIVED CORTEX EXECUTION OUTPUTS"


def _delete_count(session: Session, stmt) -> int:
    result = session.execute(stmt)
    return int(result.rowcount or 0)


def clear_derived_cortex_for_tenant(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Delete derived Cortex substrate for one tenant; keep ``raw_ingestion_records`` and ingestion ops state."""
    deleted: dict[str, int] = {}

    def _del(table, name: str) -> None:
        deleted[name] = _delete_count(session, delete(table).where(table.tenant_id == tenant_id))

    _del(DeclaredDomainMembership, "declared_domain_memberships")
    _del(DeclaredDomainStats, "declared_domain_stats")
    _del(DeclaredDomain, "declared_domains")
    _del(DeclaredDomainDirtyQueue, "declared_domain_dirty_queue")
    _del(DeclaredDomainPassRun, "declared_domain_pass_runs")

    _del(GraphRelationship, "graph_relationships")
    _del(GraphUnresolvedReference, "graph_unresolved_references")
    _del(GraphDirtyQueue, "graph_dirty_queue")
    _del(GraphPassRun, "graph_pass_runs")
    _del(GraphSchedulerTick, "graph_scheduler_ticks")

    _del(IdentitySuggestion, "identity_suggestions")
    _del(IdentityAccount, "identity_accounts")
    _del(IdentityEntity, "identity_entities")
    _del(IdentityDirtyQueue, "identity_dirty_queue")
    _del(IdentityPassRun, "identity_pass_runs")
    _del(IdentitySchedulerTick, "identity_scheduler_ticks")

    _del(CanonEntity, "canon_entities")
    _del(CanonDirtyQueue, "canon_dirty_queue")
    _del(CanonPassRun, "canon_pass_runs")
    deleted["canon_materialization_cursors"] = _delete_count(
        session,
        delete(CanonMaterializationCursor).where(CanonMaterializationCursor.tenant_id == tenant_id),
    )
    _del(CanonSchedulerTick, "canon_scheduler_ticks")

    _del(CortexPass, "cortex_passes")
    deleted["cortex_admin_continuity_snapshot"] = _delete_count(
        session,
        delete(CortexAdminContinuitySnapshot).where(
            CortexAdminContinuitySnapshot.tenant_id == tenant_id,
        ),
    )
    deleted["cortex_admin_graph_component_snapshot"] = _delete_count(
        session,
        delete(CortexAdminGraphComponentSnapshot).where(
            CortexAdminGraphComponentSnapshot.tenant_id == tenant_id,
        ),
    )

    _del(RawMemoryLineageIndex, "raw_memory_lineage_index")
    _del(RawMemoryRevisionIndex, "raw_memory_revision_index")
    _del(RawMemoryArchiveCatalog, "raw_memory_archive_catalog")
    _del(RawMemoryFailureCase, "raw_memory_failure_cases")
    _del(RawMemoryRecoveryValidation, "raw_memory_recovery_validations")
    _del(RawMemoryTrustState, "raw_memory_trust_state")
    _del(RawMemoryTrustTransition, "raw_memory_trust_transitions")
    _del(RawMemoryRetentionEvent, "raw_memory_retention_events")

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
    deleted_rows_total = sum(deleted.values())
    return {
        "tenant_id": tenant_id,
        "deleted_rows_by_table": deleted,
        "deleted_rows_total": deleted_rows_total,
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
