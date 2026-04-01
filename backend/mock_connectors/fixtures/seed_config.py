"""Scale targets and narrative constants for deterministic mock data."""

from __future__ import annotations

# Dataset baseline (strategy §14)
TARGET_REPOSITORIES = 8
TARGET_USERS = 15
TARGET_TEAMS = 6
TARGET_PROJECTS = 8
TARGET_EPICS = 30
TARGET_ISSUES = 200
TARGET_PRS = 120
TARGET_COMMITS = 800
TARGET_COMMENTS = 500
TARGET_RELATIONSHIP_EDGES = 2000

# Temporal window (strategy §12): 30–90 days
SIMULATION_DAYS = 75

ORG_NAME = "Nexora"
ORG_SLUG = "nexora"
LINEAR_KEY_PREFIX = "NEX"
GITHUB_ORG = "nexora"

REPO_NAMES = [
    "api",
    "auth-service",
    "web",
    "design-tokens",
    "mobile",
    "infra",
    "integrations",
    "data-pipeline",
]

TEAM_NAMES = [
    ("CORE", "Core API"),
    ("WEB", "Web"),
    ("MOB", "Mobile"),
    ("PLAT", "Platform"),
    ("INT", "Integrations"),
    ("DATA", "Data"),
]
