"""Scale targets and narrative constants for deterministic mock data."""

from __future__ import annotations

# Dataset baseline (strategy §14)
TARGET_REPOSITORIES = 8
TARGET_USERS = 16
TARGET_TEAMS = 6
TARGET_PROJECTS = 12
TARGET_EPICS = 45
TARGET_ISSUES = 300  # NEX-1..NEX-300 (Manager Insights scenarios use NEX-105, NEX-201..210, NEX-300)
TARGET_PRS = 120
TARGET_COMMITS = 800
TARGET_COMMENTS = 720
TARGET_RELATIONSHIP_EDGES = 2000

# Temporal window (strategy §12): 30–90 days
SIMULATION_DAYS = 120

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
