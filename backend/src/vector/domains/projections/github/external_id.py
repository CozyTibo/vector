"""Parse Step 1 external_id patterns inside the projection worker only."""

from __future__ import annotations


def parse_issue_or_pr_external_id(external_id: str) -> tuple[str, int] | None:
    """`owner/repo#num` → (\"owner/repo\", num)."""
    if "#" not in external_id:
        return None
    repo, num_s = external_id.rsplit("#", 1)
    repo = repo.strip()
    if not repo or "/" not in repo:
        return None
    try:
        num = int(num_s)
    except ValueError:
        return None
    return repo, num


def parse_commit_external_id(external_id: str) -> tuple[str, str] | None:
    """`owner/repo@sha` → (\"owner/repo\", sha)."""
    if "@" not in external_id:
        return None
    repo, sha = external_id.rsplit("@", 1)
    repo = repo.strip()
    sha = sha.strip()
    if not repo or "/" not in repo or len(sha) < 7:
        return None
    return repo, sha


def parse_pr_commit_link_external_id(external_id: str) -> tuple[str, int, str] | None:
    """`owner/repo#num@sha` → (\"owner/repo\", num, sha)."""
    if "@" not in external_id:
        return None
    left, sha = external_id.rsplit("@", 1)
    sha = sha.strip()
    if len(sha) < 7:
        return None
    pr = parse_issue_or_pr_external_id(left.strip())
    if pr is None:
        return None
    repo, num = pr
    return repo, num, sha
