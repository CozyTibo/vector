"""Per-drain counters for the GitHub projection worker."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GithubProjectionMetrics:
    raw_rows_processed: int = 0
    batches_committed: int = 0
    commits_skipped_missing_repo: int = 0
