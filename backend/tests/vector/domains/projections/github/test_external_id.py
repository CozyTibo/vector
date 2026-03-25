"""Unit tests for Step 1 external_id parsing (projection worker only)."""

from __future__ import annotations

from vector.domains.projections.github.external_id import (
    parse_commit_external_id,
    parse_issue_or_pr_external_id,
)


def test_parse_issue_or_pr_external_id() -> None:
    assert parse_issue_or_pr_external_id("acme/rocket#42") == ("acme/rocket", 42)
    assert parse_issue_or_pr_external_id("a/b#1") == ("a/b", 1)
    assert parse_issue_or_pr_external_id("no-hash") is None
    assert parse_issue_or_pr_external_id("bad#x") is None


def test_parse_commit_external_id() -> None:
    sha = "a" * 40
    assert parse_commit_external_id(f"acme/rocket@{sha}") == ("acme/rocket", sha)
    assert parse_commit_external_id("bad") is None
    assert parse_commit_external_id("no/repo@short") is None
