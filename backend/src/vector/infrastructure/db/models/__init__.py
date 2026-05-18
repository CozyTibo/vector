"""ORM models — import side effects register metadata."""

from vector.infrastructure.db.models.calls_connection_detail import CallsConnectionDetail
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_bundle_equivalence_declaration import (
    CortexBundleEquivalenceDeclaration,
)
from vector.infrastructure.db.models.cortex_org_ambiguity_record import CortexOrgAmbiguityRecord
from vector.infrastructure.db.models.cortex_org_failure_case import CortexOrgFailureCase
from vector.infrastructure.db.models.cortex_org_remediation_validation import CortexOrgRemediationValidation
from vector.infrastructure.db.models.cortex_org_verification_run import CortexOrgVerificationRun
from vector.infrastructure.db.models.cortex_identity_celery_dispatch import CortexIdentityCeleryDispatch
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_certification_archive import CortexOrgCertificationArchive
from vector.infrastructure.db.models.cortex_synthesis_certification_archive import (
    CortexSynthesisCertificationArchive,
)
from vector.infrastructure.db.models.cortex_org_identity_backfill_run import CortexOrgIdentityBackfillRun
from vector.infrastructure.db.models.cortex_org_identity_console_audit import CortexOrgIdentityConsoleAudit
from vector.infrastructure.db.models.cortex_org_primitive_instance import CortexOrgPrimitiveInstance
from vector.infrastructure.db.models.cortex_link_rule_version import CortexLinkRuleVersion
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.infrastructure.db.models.cortex_org_link_replay_job_receipt import CortexOrgLinkReplayJobReceipt
from vector.infrastructure.db.models.cortex_artifact_lineage_edge import CortexArtifactLineageEdge
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import CortexOctsDurableWalkRecord
from vector.infrastructure.db.models.cortex_octs_traversal_receipt import CortexOctsTraversalReceipt
from vector.infrastructure.db.models.cortex_octs_traversal_replay_archive import CortexOctsTraversalReplayArchive
from vector.infrastructure.db.models.cortex_pipeline_continuation import CortexPipelineContinuationState
from vector.infrastructure.db.models.cortex_retrieval_materialization_report import (
    CortexRetrievalMaterializationReport,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)
from vector.infrastructure.db.models.cortex_synthesis_activation_audit import (
    CortexSynthesisActivationAudit,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_retrieval_index_epoch import CortexRetrievalIndexEpoch
from vector.infrastructure.db.models.cortex_retrieval_query_audit import CortexRetrievalQueryAudit
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.cortex_synthesis_job_receipt import CortexSynthesisJobReceipt
from vector.infrastructure.db.models.cortex_synthesis_publication_epoch import (
    CortexSynthesisPublicationEpoch,
)
from vector.infrastructure.db.models.cortex_synthesis_retention_event import (
    CortexSynthesisRetentionEvent,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_artifact import CortexTcreReconstructionArtifact
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate
from vector.infrastructure.db.models.cortex_org_link_candidate_batch import CortexOrgLinkCandidateBatch
from vector.infrastructure.db.models.cortex_org_link_promotion_policy import CortexOrgLinkPromotionPolicy
from vector.infrastructure.db.models.cortex_org_merge import CortexOrgMerge
from vector.infrastructure.db.models.cortex_org_merge_policy import CortexOrgMergePolicy
from vector.infrastructure.db.models.cortex_canonical_provenance_record import CortexCanonicalProvenanceRecord
from vector.infrastructure.db.models.cortex_canonical_temporal_supersession import CortexCanonicalTemporalSupersession
from vector.infrastructure.db.models.cortex_canonical_certification_archive import (
    CortexCanonicalCertificationArchive,
)
from vector.infrastructure.db.models.cortex_canonical_stabilization_proof_run import (
    CortexCanonicalStabilizationProofRun,
)
from vector.infrastructure.db.models.cortex_canonical_verification_run import CortexCanonicalVerificationRun
from vector.infrastructure.db.models.cortex_canonical_replay_job import CortexCanonicalReplayJob
from vector.infrastructure.db.models.cortex_canonical_replay_job_receipt import CortexCanonicalReplayJobReceipt
from vector.infrastructure.db.models.cortex_canonical_ambiguity_lifecycle_event import (
    CortexCanonicalAmbiguityLifecycleEvent,
)
from vector.infrastructure.db.models.cortex_canonical_ambiguity_record import CortexCanonicalAmbiguityRecord
from vector.infrastructure.db.models.cortex_canonical_failure_case import CortexCanonicalFailureCase
from vector.infrastructure.db.models.cortex_canonical_field_lineage import CortexCanonicalFieldLineage
from vector.infrastructure.db.models.cortex_canonical_remediation_validation import (
    CortexCanonicalRemediationValidation,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
from vector.infrastructure.db.models.cortex_mapping_bundle_changelog import CortexMappingBundleChangelogEntry
from vector.infrastructure.db.models.cortex_mapping_bundle_compatibility import CortexMappingBundleCompatibilityEdge
from vector.infrastructure.db.models.cortex_mapping_bundle_pin import CortexMappingBundlePin
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.github_connection_detail import GithubConnectionDetail
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.identity import UserIdentity
from vector.infrastructure.db.models.linear_connection_detail import LinearConnectionDetail
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.notion_connection_detail import NotionConnectionDetail
from vector.infrastructure.db.models.onboarding_message import OnboardingMessage
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.models.password_reset_token import PasswordResetToken
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_archive_catalog import RawMemoryArchiveCatalog
from vector.infrastructure.db.models.raw_memory_failure_case import RawMemoryFailureCase
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex
from vector.infrastructure.db.models.raw_memory_retention_event import RawMemoryRetentionEvent
from vector.infrastructure.db.models.raw_memory_recovery_validation import RawMemoryRecoveryValidation
from vector.infrastructure.db.models.raw_memory_revision_index import RawMemoryRevisionIndex
from vector.infrastructure.db.models.raw_memory_trust_state import RawMemoryTrustState
from vector.infrastructure.db.models.raw_memory_trust_transition import RawMemoryTrustTransition
from vector.infrastructure.db.models.slack_connection_detail import SlackConnectionDetail
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

__all__ = [
    "ConnectorSyncState",
    "CortexBundleEquivalenceDeclaration",
    "CortexCanonicalIdentityAnchor",
    "CortexOrgAmbiguityRecord",
    "CortexOrgFailureCase",
    "CortexOrgRemediationValidation",
    "CortexOrgVerificationRun",
    "CortexIdentityCeleryDispatch",
    "CortexOrgCertificationArchive",
    "CortexOrgEntity",
    "CortexOrgIdentityBackfillRun",
    "CortexOrgIdentityConsoleAudit",
    "CortexOrgPrimitiveInstance",
    "CortexLinkRuleVersion",
    "CortexOrgLink",
    "CortexOrgLinkReplayJob",
    "CortexOrgLinkReplayJobReceipt",
    "CortexArtifactLineageEdge",
    "CortexOctsDurableWalkRecord",
    "CortexOctsTraversalReceipt",
    "CortexOctsTraversalReplayArchive",
    "CortexSubstratePhaseRun",
    "CortexSubstratePipelineRun",
    "CortexRetrievalIndexEntry",
    "CortexRetrievalIndexEpoch",
    "CortexRetrievalQueryAudit",
    "CortexSynthesisJob",
    "CortexSynthesisArtifact",
    "CortexSynthesisJobReceipt",
    "CortexTcreReconstructionArtifact",
    "CortexTcreReconstructionJob",
    "CortexOrgLinkCandidate",
    "CortexOrgLinkCandidateBatch",
    "CortexOrgLinkPromotionPolicy",
    "CortexOrgMerge",
    "CortexOrgMergePolicy",
    "CortexCanonicalProvenanceRecord",
    "CortexCanonicalTemporalSupersession",
    "CortexCanonicalCertificationArchive",
    "CortexCanonicalStabilizationProofRun",
    "CortexCanonicalVerificationRun",
    "CortexCanonicalReplayJob",
    "CortexCanonicalReplayJobReceipt",
    "CortexCanonicalAmbiguityLifecycleEvent",
    "CortexCanonicalAmbiguityRecord",
    "CortexCanonicalFailureCase",
    "CortexCanonicalFieldLineage",
    "CortexCanonicalRemediationValidation",
    "CortexCanonicalTransformMaterialization",
    "CortexMappingBundle",
    "CortexMappingBundleChangelogEntry",
    "CortexMappingBundleCompatibilityEdge",
    "CortexMappingBundlePin",
    "CallsConnectionDetail",
    "NotionConnectionDetail",
    "OnboardingMessage",
    "OnboardingState",
    "PasswordResetToken",
    "RawIngestionRecord",
    "RawMemoryArchiveCatalog",
    "RawMemoryFailureCase",
    "RawMemoryLineageIndex",
    "RawMemoryRetentionEvent",
    "RawMemoryRecoveryValidation",
    "RawMemoryRevisionIndex",
    "RawMemoryTrustState",
    "RawMemoryTrustTransition",
    "GithubConnectionDetail",
    "IngestionRun",
    "LinearConnectionDetail",
    "SlackConnectionDetail",
    "Tenant",
    "TenantConnection",
    "TenantMembership",
    "User",
    "UserIdentity",
]
