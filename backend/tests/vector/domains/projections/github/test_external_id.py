from __future__ import annotations

from vector.domains.projections.github.external_id import parse_pr_commit_link_external_id


def test_parse_pr_commit_link_external_id_ok() -> None:
    ext = "cozytibo/vector#3@abcdef1234567890abcdef1234567890abcdef12"
    assert parse_pr_commit_link_external_id(ext) == (
        "cozytibo/vector",
        3,
        "abcdef1234567890abcdef1234567890abcdef12",
    )


def test_parse_pr_commit_link_external_id_short_sha() -> None:
    assert parse_pr_commit_link_external_id("a/b#1@short") is None
