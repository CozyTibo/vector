"""Tenant-scoped Cortex flush helper for operator-triggered full reruns."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.cortex_canonical_ambiguity_lifecycle_event import (
    CortexCanonicalAmbiguityLifecycleEvent,
)
from vector.infrastructure.db.models.cortex_canonical_ambiguity_record import CortexCanonicalAmbiguityRecord
from vector.infrastructure.db.models.cortex_canonical_certification_archive import (
    CortexCanonicalCertificationArchive,
)
from vector.infrastructure.db.models.cortex_canonical_failure_case import CortexCanonicalFailureCase
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_canonical_provenance_record import CortexCanonicalProvenanceRecord
from vector.infrastructure.db.models.cortex_canonical_remediation_validation import (
    CortexCanonicalRemediationValidation,
)
from vector.infrastructure.db.models.cortex_canonical_replay_job import CortexCanonicalReplayJob
from vector.infrastructure.db.models.cortex_canonical_stabilization_proof_run import (
    CortexCanonicalStabilizationProofRun,
)
from vector.infrastructure.db.models.cortex_canonical_temporal_supersession import (
    CortexCanonicalTemporalSupersession,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_canonical_verification_run import CortexCanonicalVerificationRun
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_archive_catalog import RawMemoryArchiveCatalog
from vector.infrastructure.db.models.raw_memory_failure_case import RawMemoryFailureCase
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex
from vector.infrastructure.db.models.raw_memory_recovery_validation import RawMemoryRecoveryValidation
from vector.infrastructure.db.models.raw_memory_retention_event import RawMemoryRetentionEvent
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex
from vector.infrastructure.db.models.raw_memory_trust_state import RawMemoryTrustState
from vector.infrastructure.db.models.raw_memory_trust_transition import RawMemoryTrustTransition


def flush_tenant_cortex_pipeline_state(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Delete tenant-scoped Cortex raw + canonical runtime state."""
    delete_plan: tuple[tuple[str, type[Any]], ...] = (
        ("cortex_canonical_ambiguity_lifecycle_events", CortexCanonicalAmbiguityLifecycleEvent),
        ("cortex_canonical_ambiguity_records", CortexCanonicalAmbiguityRecord),
        ("cortex_canonical_remediation_validations", CortexCanonicalRemediationValidation),
        ("cortex_canonical_failure_cases", CortexCanonicalFailureCase),
        ("cortex_canonical_temporal_supersessions", CortexCanonicalTemporalSupersession),
        ("cortex_canonical_identity_anchors", CortexCanonicalIdentityAnchor),
        ("cortex_canonical_provenance_records", CortexCanonicalProvenanceRecord),
        ("cortex_canonical_transform_materializations", CortexCanonicalTransformMaterialization),
        ("cortex_canonical_replay_jobs", CortexCanonicalReplayJob),
        ("cortex_canonical_verification_runs", CortexCanonicalVerificationRun),
        ("cortex_canonical_stabilization_proof_runs", CortexCanonicalStabilizationProofRun),
        ("cortex_canonical_certification_archives", CortexCanonicalCertificationArchive),
        ("raw_memory_trust_transitions", RawMemoryTrustTransition),
        ("raw_memory_trust_state", RawMemoryTrustState),
        ("raw_memory_recovery_validation", RawMemoryRecoveryValidation),
        ("raw_memory_failure_cases", RawMemoryFailureCase),
        ("raw_memory_retention_events", RawMemoryRetentionEvent),
        ("raw_memory_revision_index", RawMemoryRevisionIndex),
        ("raw_memory_lineage_index", RawMemoryLineageIndex),
        ("raw_memory_archive_catalog", RawMemoryArchiveCatalog),
        ("connector_sync_state", ConnectorSyncState),
        ("raw_ingestion_records", RawIngestionRecord),
        ("ingestion_runs", IngestionRun),
    )
    deleted_by_table: dict[str, int] = {}
    for table_name, model in delete_plan:
        result = session.execute(delete(model).where(model.tenant_id == tenant_id))
        deleted_by_table[table_name] = int(result.rowcount or 0)
    session.flush()
    return {
        "tenant_id": str(tenant_id),
        "deleted_rows_by_table": deleted_by_table,
        "deleted_rows_total": sum(deleted_by_table.values()),
    }
