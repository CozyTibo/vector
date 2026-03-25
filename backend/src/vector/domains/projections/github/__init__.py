"""GitHub connector projection worker and handlers."""

from vector.domains.projections.github.metrics import GithubProjectionMetrics
from vector.domains.projections.github.worker import drain_github_projections

__all__ = [
    "GithubProjectionMetrics",
    "drain_github_projections",
]
