"""§6 Step 40 — persist dismiss as ``manager_insight_outcomes`` + decision status."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision
from vector.infrastructure.db.models.manager_insight_outcome import ManagerInsightOutcome
from vector.infrastructure.db.repositories.manager_insight_decisions import (
    get_manager_insight_decision_for_tenant,
)
from vector.infrastructure.db.repositories.manager_insight_outcomes import (
    get_latest_manager_insight_outcome_for_decision,
    insert_manager_insight_outcome_row,
)

_TERMINAL_STATUSES = frozenset({"completed", "failed"})


class ManagerInsightDismissNotFoundError(Exception):
    """No persisted decision for tenant + id."""


class ManagerInsightDismissTerminalError(Exception):
    """Decision is in a terminal lifecycle state; cannot dismiss."""

    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(status)


def persist_manager_insight_dismiss(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    decision_id: uuid.UUID,
    user_attribution: str | None = None,
    false_positive: bool | None = None,
    ground_truth: dict[str, Any] | None = None,
) -> tuple[ManagerInsightOutcome, ManagerInsightDecision, bool]:
    """Insert outcome ``dismissed``, set decision ``status`` to ``dismissed``.

    Returns ``(outcome, decision, idempotent)``. When the row is already ``dismissed`` and a
    matching outcome exists, returns that pair with ``idempotent=True`` and does not insert.
    """
    row = get_manager_insight_decision_for_tenant(
        session,
        tenant_id=tenant_id,
        decision_id=decision_id,
    )
    if row is None:
        raise ManagerInsightDismissNotFoundError()
    if row.status in _TERMINAL_STATUSES:
        raise ManagerInsightDismissTerminalError(row.status)

    if row.status == "dismissed":
        existing = get_latest_manager_insight_outcome_for_decision(
            session,
            tenant_id=tenant_id,
            decision_id=decision_id,
            outcome_type="dismissed",
        )
        if existing is not None:
            return (existing, row, True)
        outcome = insert_manager_insight_outcome_row(
            session,
            tenant_id=tenant_id,
            decision_id=decision_id,
            outcome_type="dismissed",
            false_positive=false_positive,
            ground_truth=ground_truth,
            user_attribution=user_attribution,
        )
        session.flush()
        return (outcome, row, False)

    outcome = insert_manager_insight_outcome_row(
        session,
        tenant_id=tenant_id,
        decision_id=decision_id,
        outcome_type="dismissed",
        false_positive=false_positive,
        ground_truth=ground_truth,
        user_attribution=user_attribution,
    )
    row.status = "dismissed"
    session.flush()
    return (outcome, row, False)


__all__ = [
    "ManagerInsightDismissNotFoundError",
    "ManagerInsightDismissTerminalError",
    "persist_manager_insight_dismiss",
]
