"""Onboarding step IDs and status values (product + API)."""

from __future__ import annotations

# Chat-first profile collection (single step; phases live in answers_json.profile_phase).
STEP_CHAT_PROFILE = "CHAT_PROFILE"

# Connector nudges (Slack planned; GitHub/Linear use existing OAuth flows).
STEP_CONNECT_SLACK = "CONNECT_SLACK"
STEP_CONNECT_GITHUB = "CONNECT_GITHUB"
STEP_CONNECT_LINEAR = "CONNECT_LINEAR"

STEP_SCANNING = "SCANNING"
STEP_THANK_YOU = "THANK_YOU"

ONBOARDING_STEPS: frozenset[str] = frozenset(
    {
        STEP_CHAT_PROFILE,
        STEP_CONNECT_SLACK,
        STEP_CONNECT_GITHUB,
        STEP_CONNECT_LINEAR,
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
PROFILE_PHASE_TOOLS = "tools"
PROFILE_PHASE_DONE = "done"

PROFILE_PHASES_ORDER: tuple[str, ...] = (
    PROFILE_PHASE_NAME,
    PROFILE_PHASE_ORG,
    PROFILE_PHASE_ROLE,
    PROFILE_PHASE_WEBSITE,
    PROFILE_PHASE_SIZE,
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
    {"communication", "engineering", "pm", "docs"},
)
