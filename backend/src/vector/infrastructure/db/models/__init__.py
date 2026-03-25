"""ORM models — import side effects register metadata."""

from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.github_connection_detail import GithubConnectionDetail
from vector.infrastructure.db.models.identity import UserIdentity
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.linear_connection_detail import LinearConnectionDetail
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

__all__ = [
    "ConnectorSyncState",
    "GithubConnectionDetail",
    "IngestionRun",
    "LinearConnectionDetail",
    "RawIngestionRecord",
    "Tenant",
    "TenantConnection",
    "TenantMembership",
    "User",
    "UserIdentity",
]
