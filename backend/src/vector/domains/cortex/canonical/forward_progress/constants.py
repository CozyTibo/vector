"""Canonical forward-progress runtime constants."""

from __future__ import annotations

from typing import Final

FORWARD_PROGRESS_SCHEMA_VERSION: Final[int] = 1

# Canonical drain / phase outcomes (truthful operator semantics).
CANONICAL_OUTCOME_PROGRESSED: Final[str] = "progressed"
CANONICAL_OUTCOME_PARTIAL_PROGRESS: Final[str] = "partial_progress"
CANONICAL_OUTCOME_TOPOLOGY_WAIT: Final[str] = "topology_wait"
CANONICAL_OUTCOME_IDLE: Final[str] = "idle"
CANONICAL_OUTCOME_FAILED: Final[str] = "failed"

# Deferral reasons (persisted for operators).
DEFERRAL_REASON_MISSING_PARENT: Final[str] = "missing_parent"
DEFERRAL_REASON_MISSING_PARENT_COMMIT: Final[str] = "missing_parent_commit"
DEFERRAL_REASON_MISSING_PR: Final[str] = "missing_pr"
DEFERRAL_REASON_MISSING_DEPLOYMENT: Final[str] = "missing_deployment"
DEFERRAL_REASON_MISSING_PAGE_PARENT: Final[str] = "missing_page_parent"
DEFERRAL_REASON_DEPENDENCY_NOT_MATERIALIZED: Final[str] = "dependency_not_materialized"
DEFERRAL_REASON_TOPOLOGY_ORPHAN: Final[str] = "topology_orphan"

DEFERRAL_QUEUE_EXTERNAL_PARENT: Final[str] = "external_parent_unmaterialized"
DEFERRAL_QUEUE_TOPOLOGY_ORPHAN: Final[str] = "topology_orphan"
