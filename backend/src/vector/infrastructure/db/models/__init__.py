"""ORM models — import side effects register metadata."""

from vector.infrastructure.db.models.calls_connection_detail import CallsConnectionDetail
from vector.infrastructure.db.models.github_connection_detail import GithubConnectionDetail
from vector.infrastructure.db.models.identity import UserIdentity
from vector.infrastructure.db.models.linear_connection_detail import LinearConnectionDetail
from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision
from vector.infrastructure.db.models.manager_insight_outcome import ManagerInsightOutcome
from vector.infrastructure.db.models.manager_insight_policy_counter import (
    ManagerInsightPolicyCounter,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.notion_connection_detail import NotionConnectionDetail
from vector.infrastructure.db.models.onboarding_message import OnboardingMessage
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.models.password_reset_token import PasswordResetToken
from vector.infrastructure.db.models.slack_connection_detail import SlackConnectionDetail
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

__all__ = [
    "CallsConnectionDetail",
    "NotionConnectionDetail",
    "OnboardingMessage",
    "OnboardingState",
    "PasswordResetToken",
    "GithubConnectionDetail",
    "LinearConnectionDetail",
    "ManagerInsightDecision",
    "ManagerInsightOutcome",
    "ManagerInsightPolicyCounter",
    "SlackConnectionDetail",
    "Tenant",
    "TenantConnection",
    "TenantMembership",
    "User",
    "UserIdentity",
]
