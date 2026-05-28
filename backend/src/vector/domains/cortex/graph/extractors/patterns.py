"""Deterministic reference patterns (phase 1+)."""

from __future__ import annotations

import re

# Linear ticket identifiers e.g. LIN-123
LINEAR_IDENTIFIER_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-\d+)\b")

# https://github.com/org/repo/pull/42
GITHUB_PR_URL_RE = re.compile(
    r"https://github\.com/([^/\s]+)/([^/\s]+)/pull/(\d+)",
    re.IGNORECASE,
)
GITHUB_ISSUE_URL_RE = re.compile(
    r"https://github\.com/([^/\s]+)/([^/\s]+)/issues/(\d+)",
    re.IGNORECASE,
)
GITHUB_COMMIT_URL_RE = re.compile(
    r"https://github\.com/([^/\s]+)/([^/\s]+)/commit/([0-9a-fA-F]{7,40})",
    re.IGNORECASE,
)

# owner/repo#123 when repo scope known
GITHUB_SHORTHAND_RE = re.compile(r"\b([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)#(\d+)\b")

# #123 when repo full_name scope known (PR vs issue disambiguated by context words)
GITHUB_HASH_NUM_RE = re.compile(r"(?<!\w)#(\d+)\b")

MAX_TEXT_SCAN_CHARS = 8000
