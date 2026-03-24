"""ORM models — import side effects register metadata."""

from vector.infrastructure.db.models.identity import UserIdentity
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

__all__ = [
    "Tenant",
    "TenantMembership",
    "User",
    "UserIdentity",
]

