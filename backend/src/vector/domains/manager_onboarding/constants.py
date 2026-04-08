"""Step ids and statuses for manager Slack onboarding."""

from __future__ import annotations

# Steps (canonical order for "first unanswered")
STEP_Q1_SCOPE_INTENT = "Q1_SCOPE_INTENT"
STEP_Q1B_PEER_HANDLES = "Q1B_PEER_HANDLES"
STEP_Q2_TEAM_SCOPE = "Q2_TEAM_SCOPE"
STEP_Q3_TEAM_MEMBERS = "Q3_TEAM_MEMBERS"
STEP_Q4_OBSERVED_CHANNELS = "Q4_OBSERVED_CHANNELS"
STEP_Q5_REPORTS_TO = "Q5_REPORTS_TO"
STEP_Q5B_REPORTS_WHO = "Q5B_REPORTS_WHO"
STEP_Q6_KPIS = "Q6_KPIS"
STEP_COMPLETED = "COMPLETED"

STEP_ORDER: tuple[str, ...] = (
    STEP_Q1_SCOPE_INTENT,
    STEP_Q1B_PEER_HANDLES,
    STEP_Q2_TEAM_SCOPE,
    STEP_Q3_TEAM_MEMBERS,
    STEP_Q4_OBSERVED_CHANNELS,
    STEP_Q5_REPORTS_TO,
    STEP_Q5B_REPORTS_WHO,
    STEP_Q6_KPIS,
    STEP_COMPLETED,
)

STATUS_ACTIVE = "active"
STATUS_WAITING_FOR_USER = "waiting_for_user"
STATUS_COMPLETED = "completed"
STATUS_PAUSED = "paused"
STATUS_FAILED = "failed"
STATUS_NEEDS_REVIEW = "needs_review"

SCOPE_JUST_ME = "just_me"
SCOPE_OTHER_MANAGERS = "other_managers"

# Safety (spec)
MAX_CLARIFICATIONS_PER_STEP = 2
MAX_MESSAGES_PER_STEP = 4
# Q4 often needs back-and-forth (invites, plain #channel names); allow more before watchdog.
MAX_MESSAGES_PER_STEP_Q4_CHANNELS = 12

# Block Kit action_ids (each must be unique within a single message — duplicates → invalid_blocks)
ACTION_SCOPE_JUST_ME = "manager_ob_scope_just_me"
ACTION_SCOPE_OTHER_MGR = "manager_ob_scope_other_mgr"
ACTION_REPORTS_YES = "manager_ob_reports_yes"
ACTION_REPORTS_NO = "manager_ob_reports_no"

# Dedupe / idempotency prefixes
OUTBOUND_INTRO_KEY = "intro"
OUTBOUND_STEP_REPLY_KEY = "step_reply"
