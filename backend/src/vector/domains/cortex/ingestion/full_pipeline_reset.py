"""Tenant-scoped Cortex flush helper for operator-triggered full reruns."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.cortex_canonical_ambiguity_lifecycle_event import (
    CortexCanonicalAmbiguityLifecycleEvent,
)
from vector.infrastructure.db.models.cortex_canonical_ambiguity_record import (
    CortexCanonicalAmbiguityRecord,
)
from vector.infrastructure.db.models.cortex_canonical_certification_archive import (
    CortexCanonicalCertificationArchive,
)
from vector.infrastructure.db.models.cortex_canonical_failure_case import CortexCanonicalFailureCase
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import (
    CortexCanonicalIdentityAnchor,
)
from vector.infrastructure.db.models.cortex_canonical_provenance_record import (
    CortexCanonicalProvenanceRecord,
)
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
from vector.infrastructure.db.models.cortex_canonical_verification_run import (
    CortexCanonicalVerificationRun,
)
from vector.infrastructure.db.models.cortex_identity_celery_dispatch import (
    CortexIdentityCeleryDispatch,
)
from vector.infrastructure.db.models.cortex_org_ambiguity_record import CortexOrgAmbiguityRecord
from vector.infrastructure.db.models.cortex_org_certification_archive import (
    CortexOrgCertificationArchive,
)
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_failure_case import CortexOrgFailureCase
from vector.infrastructure.db.models.cortex_org_identity_backfill_run import (
    CortexOrgIdentityBackfillRun,
)
from vector.infrastructure.db.models.cortex_org_identity_console_audit import (
    CortexOrgIdentityConsoleAudit,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate
from vector.infrastructure.db.models.cortex_org_link_candidate_batch import (
    CortexOrgLinkCandidateBatch,
)
from vector.infrastructure.db.models.cortex_org_link_promotion_policy import (
    CortexOrgLinkPromotionPolicy,
)
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.infrastructure.db.models.cortex_org_link_replay_job_receipt import (
    CortexOrgLinkReplayJobReceipt,
)
from vector.infrastructure.db.models.cortex_org_merge import CortexOrgMerge
from vector.infrastructure.db.models.cortex_org_merge_policy import CortexOrgMergePolicy
from vector.infrastructure.db.models.cortex_org_primitive_instance import CortexOrgPrimitiveInstance
from vector.infrastructure.db.models.cortex_org_remediation_validation import (
    CortexOrgRemediationValidation,
)
from vector.infrastructure.db.models.cortex_org_verification_run import CortexOrgVerificationRun
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_archive_catalog import RawMemoryArchiveCatalog
from vector.infrastructure.db.models.raw_memory_failure_case import RawMemoryFailureCase
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex
from vector.infrastructure.db.models.raw_memory_recovery_validation import (
    RawMemoryRecoveryValidation,
)
from vector.infrastructure.db.models.raw_memory_retention_event import RawMemoryRetentionEvent
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex
from vector.infrastructure.db.models.raw_memory_trust_state import RawMemoryTrustState
from vector.infrastructure.db.models.raw_memory_trust_transition import RawMemoryTrustTransition


def _flush_phase04_org_identity_tables(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    """Delete tenant-scoped Phase 04 org identity / operator-console rows (FK-safe order)."""
    deleted: dict[str, int] = {}
    job_ids = list(
        session.scalars(
            select(CortexOrgLinkReplayJob.id).where(CortexOrgLinkReplayJob.tenant_id == tenant_id),
        ).all()
    )
    if job_ids:
        r = session.execute(
            delete(CortexOrgLinkReplayJobReceipt).where(CortexOrgLinkReplayJobReceipt.job_id.in_(job_ids))
        )
        deleted["cortex_org_link_replay_job_receipts"] = int(r.rowcount or 0)
    else:
        deleted["cortex_org_link_replay_job_receipts"] = 0
    r = session.execute(
        delete(CortexOrgLinkReplayJob).where(CortexOrgLinkReplayJob.tenant_id == tenant_id),
    )
    deleted["cortex_org_link_replay_jobs"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexIdentityCeleryDispatch).where(
            CortexIdentityCeleryDispatch.tenant_id == tenant_id,
        ),
    )
    deleted["cortex_identity_celery_dispatches"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexOrgIdentityConsoleAudit).where(
            CortexOrgIdentityConsoleAudit.tenant_id == tenant_id,
        ),
    )
    deleted["cortex_org_identity_console_audits"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexOrgCertificationArchive).where(
            CortexOrgCertificationArchive.tenant_id == tenant_id,
        ),
    )
    deleted["cortex_org_certification_archives"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexOrgVerificationRun).where(CortexOrgVerificationRun.tenant_id == tenant_id)
    )
    deleted["cortex_org_verification_runs"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexOrgRemediationValidation).where(
            CortexOrgRemediationValidation.tenant_id == tenant_id,
        ),
    )
    deleted["cortex_org_remediation_validations"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexOrgFailureCase).where(CortexOrgFailureCase.tenant_id == tenant_id),
    )
    deleted["cortex_org_failure_cases"] = int(r.rowcount or 0)
    session.execute(
        update(CortexOrgAmbiguityRecord)
        .where(CortexOrgAmbiguityRecord.tenant_id == tenant_id)
        .values(superseded_by_org_ambiguity_id=None)
    )
    r = session.execute(
        delete(CortexOrgAmbiguityRecord).where(CortexOrgAmbiguityRecord.tenant_id == tenant_id)
    )
    deleted["cortex_org_ambiguity_records"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexOrgPrimitiveInstance).where(CortexOrgPrimitiveInstance.tenant_id == tenant_id)
    )
    deleted["cortex_org_primitive_instances"] = int(r.rowcount or 0)
    r = session.execute(delete(CortexOrgLink).where(CortexOrgLink.tenant_id == tenant_id))
    deleted["cortex_org_links"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexOrgLinkCandidate).where(CortexOrgLinkCandidate.tenant_id == tenant_id)
    )
    deleted["cortex_org_link_candidates"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexOrgLinkCandidateBatch).where(
            CortexOrgLinkCandidateBatch.tenant_id == tenant_id,
        ),
    )
    deleted["cortex_org_link_candidate_batches"] = int(r.rowcount or 0)
    session.execute(
        update(CortexOrgMerge)
        .where(CortexOrgMerge.tenant_id == tenant_id)
        .values(supersedes_merge_id=None),
    )
    r = session.execute(
        delete(CortexOrgMerge).where(CortexOrgMerge.tenant_id == tenant_id),
    )
    deleted["cortex_org_merges"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexOrgMergePolicy).where(CortexOrgMergePolicy.tenant_id == tenant_id),
    )
    deleted["cortex_org_merge_policies"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexOrgLinkPromotionPolicy).where(
            CortexOrgLinkPromotionPolicy.tenant_id == tenant_id,
        ),
    )
    deleted["cortex_org_link_promotion_policies"] = int(r.rowcount or 0)
    r = session.execute(
        delete(CortexOrgIdentityBackfillRun).where(
            CortexOrgIdentityBackfillRun.tenant_id == tenant_id,
        ),
    )
    deleted["cortex_org_identity_backfill_runs"] = int(r.rowcount or 0)
    r = session.execute(delete(CortexOrgEntity).where(CortexOrgEntity.tenant_id == tenant_id))
    deleted["cortex_org_entities"] = int(r.rowcount or 0)
    session.flush()
    return deleted


def flush_tenant_cortex_pipeline_state(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Delete tenant-scoped Cortex raw + canonical runtime state + Phase 04 org identity rows."""
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
    org_deleted = _flush_phase04_org_identity_tables(session, tenant_id=tenant_id)
    deleted_by_table.update(org_deleted)
    session.flush()
    return {
        "tenant_id": str(tenant_id),
        "deleted_rows_by_table": deleted_by_table,
        "deleted_rows_total": sum(deleted_by_table.values()),
    }
