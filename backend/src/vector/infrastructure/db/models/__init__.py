"""ORM models — import side effects register metadata."""

from vector.infrastructure.db.models.calls_connection_detail import CallsConnectionDetail
from vector.infrastructure.db.models.canon_dirty_queue import CanonDirtyQueue
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.canon_materialization_cursor import CanonMaterializationCursor
from vector.infrastructure.db.models.canon_pass_run import CanonPassRun
from vector.infrastructure.db.models.canon_scheduler_tick import CanonSchedulerTick
from vector.infrastructure.db.models.cortex_admin_continuity_snapshot import CortexAdminContinuitySnapshot
from vector.infrastructure.db.models.cortex_pass import CortexPass
from vector.infrastructure.db.models.graph_dirty_queue import GraphDirtyQueue
from vector.infrastructure.db.models.graph_pass_run import GraphPassRun
from vector.infrastructure.db.models.graph_relationship import GraphRelationship
from vector.infrastructure.db.models.graph_scheduler_tick import GraphSchedulerTick
from vector.infrastructure.db.models.graph_unresolved_reference import GraphUnresolvedReference
from vector.infrastructure.db.models.cortex_admin_graph_component_snapshot import (
    CortexAdminGraphComponentSnapshot,
)
from vector.infrastructure.db.models.cortex_phase09_readiness_signoff import (
    CortexPhase09ReadinessSignoff,
)
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.github_connection_detail import GithubConnectionDetail
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.ingestion_scheduler_tick import IngestionSchedulerTick
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_dirty_queue import IdentityDirtyQueue
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.identity_pass_run import IdentityPassRun
from vector.infrastructure.db.models.identity_scheduler_tick import IdentitySchedulerTick
from vector.infrastructure.db.models.identity_suggestion import IdentitySuggestion
from vector.infrastructure.db.models.identity import UserIdentity
from vector.infrastructure.db.models.linear_connection_detail import LinearConnectionDetail
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.notion_connection_detail import NotionConnectionDetail
from vector.infrastructure.db.models.onboarding_message import OnboardingMessage
from vector.infrastructure.db.models.orchestrator_run import OrchestratorRun
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
    "CanonDirtyQueue",
    "CanonEntity",
    "CanonEntitySource",
    "CanonMaterializationCursor",
    "CanonPassRun",
    "CanonSchedulerTick",
    "CallsConnectionDetail",
    "ConnectorSyncState",
    "CortexAdminContinuitySnapshot",
    "CortexPass",
    "GraphDirtyQueue",
    "GraphPassRun",
    "GraphRelationship",
    "GraphSchedulerTick",
    "GraphUnresolvedReference",
    "CortexAdminGraphComponentSnapshot",
    "CortexPhase09ReadinessSignoff",
    "GithubConnectionDetail",
    "IngestionRun",
    "IngestionSchedulerTick",
    "IdentityAccount",
    "IdentityDirtyQueue",
    "IdentityEntity",
    "IdentityPassRun",
    "IdentitySchedulerTick",
    "IdentitySuggestion",
    "LinearConnectionDetail",
    "NotionConnectionDetail",
    "OnboardingMessage",
    "OrchestratorRun",
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
    "SlackConnectionDetail",
    "Tenant",
    "TenantConnection",
    "TenantMembership",
    "User",
    "UserIdentity",
]
