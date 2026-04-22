"""Onboarding step IDs and status values (product + API)."""

from __future__ import annotations

# Chat-first profile collection (single step; phases live in answers_json.profile_phase).
STEP_CHAT_PROFILE = "CHAT_PROFILE"

# Connector OAuth screens (order is driven by `connect_queue` in answers).
# Typical queue: Linear (PM) → GitHub (engineering) → Slack or Teams/Discord placeholder.
STEP_CONNECT_PROJECT_MANAGEMENT = "CONNECT_PROJECT_MANAGEMENT"
STEP_CONNECT_ENGINEERING = "CONNECT_ENGINEERING"
# Communication phase: Slack OAuth; legacy rows may still have ``comm_placeholder`` in ``connect_queue``.
STEP_CONNECT_COMMUNICATION = "CONNECT_COMMUNICATION"

# Mandatory tool picks include categories Vector does not connect in onboarding yet (e.g. Teams-only,
# or PM/engineering outside Linear/GitHub). In-product apology + finish or edit tools.
STEP_UNSUPPORTED_MANDATORY_TOOLS = "UNSUPPORTED_MANDATORY_TOOLS"

# After Slack OAuth: pick managers/people with @-mention autocomplete (Slack workspace roster).
STEP_SLACK_STAKEHOLDERS = "SLACK_STAKEHOLDERS"

# After stakeholders are saved: product UI shows a short in-chat farewell then app CTA.
STEP_ADMIN_ACCESS = "ADMIN_ACCESS"

STEP_SCANNING = "SCANNING"
STEP_THANK_YOU = "THANK_YOU"

ONBOARDING_STEPS: frozenset[str] = frozenset(
    {
        STEP_CHAT_PROFILE,
        STEP_CONNECT_PROJECT_MANAGEMENT,
        STEP_CONNECT_ENGINEERING,
        STEP_CONNECT_COMMUNICATION,
        STEP_UNSUPPORTED_MANDATORY_TOOLS,
        STEP_SLACK_STAKEHOLDERS,
        STEP_ADMIN_ACCESS,
        STEP_SCANNING,
        STEP_THANK_YOU,
    },
)

STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_ABANDONED = "abandoned"

# Internal profile sub-phases (stored in answers_json.profile_phase).
PROFILE_PHASE_NAME = "name"
PROFILE_PHASE_ORG = "org"
PROFILE_PHASE_ROLE = "role"
PROFILE_PHASE_WEBSITE = "website"
PROFILE_PHASE_SIZE = "size"
# Privacy / connectors Q&A before tool picker (chat-only; advance via structured_action).
PROFILE_PHASE_CONNECTORS_INTRO = "connectors_intro"
PROFILE_PHASE_TOOLS = "tools"
PROFILE_PHASE_DONE = "done"

PROFILE_PHASES_ORDER: tuple[str, ...] = (
    PROFILE_PHASE_NAME,
    PROFILE_PHASE_ORG,
    PROFILE_PHASE_ROLE,
    PROFILE_PHASE_SIZE,
    PROFILE_PHASE_CONNECTORS_INTRO,
    PROFILE_PHASE_TOOLS,
    PROFILE_PHASE_DONE,
)

ALLOWED_COMPANY_SIZES: frozenset[str] = frozenset({"1-5", "5-15", "15-50", "50+"})

# Free-text role answers are normalized into one of these (plus PROFILE_ROLE_OTHER).
# Keep granular enough for analytics; unknown free text maps to Other.
ONBOARDING_PROFILE_ROLE_CANONICAL: tuple[str, ...] = (
    "Founder",
    "Co-founder",
    "CEO",
    "CTO",
    "CFO",
    "COO",
    "VP Engineering",
    "VP Product",
    "VP Sales",
    "VP Marketing",
    "Director",
    "Head of Engineering",
    "Head of Product",
    "Head of Design",
    "Engineering Manager",
    "Program Manager",
    "Project Manager",
    "Product Manager",
    "Product Marketing Manager",
    "Technical Lead",
    "Team Lead",
    "Staff Engineer",
    "Principal Engineer",
    "Engineer",
    "Software Engineer",
    "Senior Engineer",
    "Founding Engineer",
    "DevOps",
    "SRE",
    "Data Engineer",
    "Data Scientist",
    "Machine Learning Engineer",
    "Security Engineer",
    "QA Engineer",
    "Designer",
    "Product Designer",
    "UX Designer",
    "Researcher",
    "Analyst",
    "Data Analyst",
    "Consultant",
    "Manager",
    "Sales Manager",
    "Account Executive",
    "Customer Success",
    "Marketing",
    "Sales",
    "Operations",
    "People",
    "HR",
    "Recruiter",
    "Legal",
    "Finance",
    "Support",
)

PROFILE_ROLE_OTHER = "Other"

ONBOARDING_PROFILE_ROLE_VALUES: frozenset[str] = frozenset(
    ONBOARDING_PROFILE_ROLE_CANONICAL + (PROFILE_ROLE_OTHER,)
)

TOOL_CATEGORY_KEYS: frozenset[str] = frozenset(
    {"communication", "pm", "engineering", "calls", "docs", "calendars"},
)

# Stored in ``answers_json.tools.<category>`` as string ids. Keep in sync with
# ``frontend/src/components/onboarding/onboardingToolGroups.ts`` (section order there).
ONBOARDING_TOOL_OPTIONS: tuple[tuple[str, str, str], ...] = (
    ("communication", "slack", "Slack"),
    ("communication", "ms_teams", "Microsoft Teams"),
    ("communication", "discord", "Discord"),
    ("pm", "linear", "Linear"),
    ("pm", "jira", "Jira"),
    ("pm", "clickup", "ClickUp"),
    ("engineering", "github", "GitHub"),
    ("engineering", "gitlab", "GitLab"),
    ("engineering", "bitbucket", "Bitbucket"),
    ("calls", "zoom", "Zoom"),
    ("calls", "google_meet", "Google Meet"),
    ("calls", "ms_teams", "Microsoft Teams"),
    ("calls", "webex", "Webex"),
    ("docs", "notion", "Notion"),
    ("docs", "confluence", "Confluence"),
    ("docs", "google_docs", "Google Docs"),
    ("calendars", "google_calendar", "Google Calendar"),
    ("calendars", "outlook_calendar", "Outlook / Microsoft 365"),
    ("calendars", "apple_calendar", "Apple Calendar"),
    ("calendars", "calendly", "Calendly"),
)


def onboarding_tool_ids_for_category(category: str) -> frozenset[str]:
    return frozenset(tid for cat, tid, _ in ONBOARDING_TOOL_OPTIONS if cat == category)


ONBOARDING_ALL_TOOL_IDS: frozenset[str] = frozenset(tid for _, tid, _ in ONBOARDING_TOOL_OPTIONS)
