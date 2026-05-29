"""Deterministic reference patterns (phase 1+)."""

from __future__ import annotations

import re

# Linear ticket identifiers e.g. LIN-123
LINEAR_IDENTIFIER_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-\d+)\b")

# https://linear.app/team/issue/NEX-105 or https://linear.app/nexora/NEX-105
LINEAR_ISSUE_URL_RE = re.compile(
    r"https://linear\.app/(?:[a-z0-9-]+/)?(?:issue/)?([A-Z][A-Z0-9]{1,9}-\d+)\b",
    re.IGNORECASE,
)

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

# owner/repo#123
GITHUB_SHORTHAND_RE = re.compile(r"\b([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)#(\d+)\b")

# #123 when repo full_name scope known (PR vs issue disambiguated by context words)
GITHUB_HASH_NUM_RE = re.compile(r"(?<!\w)#(\d+)\b")

MAX_TEXT_SCAN_CHARS = 8000

_NOTION_PAGE_ID = (
    r"([0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)
NOTION_PAGE_URL_RE = re.compile(
    rf"https://(?:www\.)?notion\.so/(?:[^/\s?#]+/)*(?:[^/\s?#]+-)?{_NOTION_PAGE_ID}",
    re.IGNORECASE,
)
NOTION_SITE_URL_RE = re.compile(
    rf"https://[a-z0-9-]+\.notion\.site/(?:[^?\s#]+-)?{_NOTION_PAGE_ID}",
    re.IGNORECASE,
)

SLACK_USER_MENTION_RE = re.compile(r"<@([A-Z0-9]+)>")

# https://workspace.slack.com/archives/C123/p1673610318400629 (optional |label> suffix in message text)
SLACK_ARCHIVE_URL_RE = re.compile(
    r"https?://[^/\s]+\.slack\.com/archives/([A-Z0-9]+)/p([0-9]+)",
    re.IGNORECASE,
)

GITHUB_AT_MENTION_RE = re.compile(r"@([A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)")
