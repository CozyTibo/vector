"""ORM models — import side effects register metadata."""

from vector.infrastructure.db.models.canonical import (
    Actor,
    ActorExternalIdentity,
    Artifact,
    ArtifactChangeset,
    ArtifactKind,
    ArtifactRepository,
    ArtifactRevision,
    ArtifactTrackableUnit,
    CurrentMapping,
    ExternalReference,
    MappingEvent,
    RelationKind,
    Relationship,
    Step3CanonicalCursor,
)
from vector.infrastructure.db.models.connector_projection_progress import (
    ConnectorProjectionProgress,
)
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.github_connection_detail import GithubConnectionDetail
from vector.infrastructure.db.models.github_projection import (
    GithubCommit,
    GithubIssue,
    GithubPullRequest,
    GithubRepository,
    GithubUser,
)
from vector.infrastructure.db.models.identity import UserIdentity
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.linear_connection_detail import LinearConnectionDetail
from vector.infrastructure.db.models.linear_projection import (
    LinearIssue,
    LinearIssueComment,
    LinearProject,
    LinearTeam,
    LinearUser,
)
from vector.infrastructure.db.models.manager_onboarding_channel_observation import (
    ManagerOnboardingChannelObservation,
)
from vector.infrastructure.db.models.manager_onboarding_invitation import ManagerOnboardingInvitation
from vector.infrastructure.db.models.manager_onboarding_message import ManagerOnboardingMessage
from vector.infrastructure.db.models.manager_onboarding_parse_artifact import (
    ManagerOnboardingParseArtifact,
)
from vector.infrastructure.db.models.manager_onboarding_session import ManagerOnboardingSession
from vector.infrastructure.db.models.manager_onboarding_slack_event_dedup import (
    ManagerOnboardingSlackEventDedup,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.onboarding_message import OnboardingMessage
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.slack_connection_detail import SlackConnectionDetail
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

__all__ = [
    "Actor",
    "ActorExternalIdentity",
    "Artifact",
    "ArtifactChangeset",
    "ArtifactKind",
    "ArtifactRepository",
    "ArtifactRevision",
    "ArtifactTrackableUnit",
    "ConnectorProjectionProgress",
    "CurrentMapping",
    "ExternalReference",
    "MappingEvent",
    "OnboardingMessage",
    "OnboardingState",
    "RelationKind",
    "Relationship",
    "Step3CanonicalCursor",
    "ConnectorSyncState",
    "GithubCommit",
    "GithubConnectionDetail",
    "GithubIssue",
    "GithubPullRequest",
    "GithubRepository",
    "GithubUser",
    "IngestionRun",
    "LinearConnectionDetail",
    "LinearIssue",
    "LinearIssueComment",
    "LinearProject",
    "LinearTeam",
    "LinearUser",
    "ManagerOnboardingChannelObservation",
    "ManagerOnboardingInvitation",
    "ManagerOnboardingMessage",
    "ManagerOnboardingParseArtifact",
    "ManagerOnboardingSession",
    "ManagerOnboardingSlackEventDedup",
    "SlackConnectionDetail",
    "RawIngestionRecord",
    "Tenant",
    "TenantConnection",
    "TenantMembership",
    "User",
    "UserIdentity",
]
