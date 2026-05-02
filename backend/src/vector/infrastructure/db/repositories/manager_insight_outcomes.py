"""§6 Step 39 — read paths for ``manager_insight_outcomes`` (+ helpers for tests / Step 40+)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision
from vector.infrastructure.db.models.manager_insight_outcome import ManagerInsightOutcome
from vector.infrastructure.db.models.manager_insight_policy_counter import (
    ManagerInsightPolicyCounter,
)


@dataclass(frozen=True)
class ManagerInsightOutcomeListPage:
    items: list[ManagerInsightOutcome]
    total: int


def get_latest_manager_insight_outcome_for_decision(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    decision_id: uuid.UUID,
    outcome_type: str,
) -> ManagerInsightOutcome | None:
    """Most recent outcome for a decision + type (idempotent dismiss / §6 Step 40)."""
    stmt = (
        select(ManagerInsightOutcome)
        .where(
            ManagerInsightOutcome.tenant_id == tenant_id,
            ManagerInsightOutcome.decision_id == decision_id,
            ManagerInsightOutcome.outcome_type == outcome_type,
        )
        .order_by(ManagerInsightOutcome.observed_at.desc(), ManagerInsightOutcome.id.desc())
        .limit(1)
    )
    return session.scalar(stmt)


def list_manager_insight_outcomes_chronological(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    scan_limit: int = 800,
) -> list[ManagerInsightOutcome]:
    """Oldest-first scan list for §6 Step 41 batch evaluation (deterministic order)."""
    stmt = (
        select(ManagerInsightOutcome)
        .where(ManagerInsightOutcome.tenant_id == tenant_id)
        .order_by(ManagerInsightOutcome.observed_at.asc(), ManagerInsightOutcome.id.asc())
        .limit(scan_limit)
    )
    return list(session.scalars(stmt).all())


def list_manager_insight_outcomes_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> ManagerInsightOutcomeListPage:
    """Paginated outcomes for admin list (§6 Step 39)."""
    where_clause = ManagerInsightOutcome.tenant_id == tenant_id
    total = session.scalar(select(func.count()).select_from(ManagerInsightOutcome).where(where_clause))
    if total is None:
        total = 0
    stmt = (
        select(ManagerInsightOutcome)
        .where(where_clause)
        .order_by(ManagerInsightOutcome.observed_at.desc(), ManagerInsightOutcome.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = list(session.scalars(stmt).all())
    return ManagerInsightOutcomeListPage(items=rows, total=total)


def insert_manager_insight_outcome_row(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    decision_id: uuid.UUID,
    outcome_type: str,
    observed_at: datetime | None = None,
    false_positive: bool | None = None,
    ground_truth: dict[str, Any] | None = None,
    user_attribution: str | None = None,
    row_id: uuid.UUID | None = None,
) -> ManagerInsightOutcome:
    """Insert one outcome row (integration tests / future Step 40)."""
    oid = row_id or uuid.uuid4()
    row = ManagerInsightOutcome(
        id=oid,
        tenant_id=tenant_id,
        decision_id=decision_id,
        observed_at=observed_at if observed_at is not None else datetime.now(tz=UTC),
        outcome_type=outcome_type,
        false_positive=false_positive,
        ground_truth=ground_truth if ground_truth is not None else {},
        user_attribution=user_attribution,
    )
    session.add(row)
    session.flush()
    return row


def gap_type_from_policy_dimension(dimension: str) -> str | None:
    """Return gap_type for ``dimension`` values like ``gap_type:blocker_not_tracked``; else None."""
    if not dimension.startswith("gap_type:"):
        return None
    _, _, rest = dimension.partition(":")
    return rest or None


def fetch_gap_type_policy_for_decision_sort(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    window_start: datetime,
    as_of: datetime,
) -> dict[str, tuple[int, bool]]:
    """§6 Step 42 — per ``gap_type``: ``(false_positive_count, suppressed)`` from policy counter rows.

    Uses rows with ``window_start`` in ``[window_start, as_of]`` and ``dimension`` prefix ``gap_type:``.
    ``false_positive_count`` comes from the row with the **latest** ``window_start`` per gap type.
    ``suppressed`` is true if **any** matching row has ``suppress_until`` strictly after ``as_of``.
    """
    stmt = (
        select(ManagerInsightPolicyCounter)
        .where(
            ManagerInsightPolicyCounter.tenant_id == tenant_id,
            ManagerInsightPolicyCounter.window_start >= window_start,
            ManagerInsightPolicyCounter.window_start <= as_of,
            ManagerInsightPolicyCounter.dimension.startswith("gap_type:"),
        )
    )
    rows = list(session.scalars(stmt).all())
    latest_fp: dict[str, tuple[int, datetime]] = {}
    suppressed: dict[str, bool] = {}
    for r in rows:
        gt = gap_type_from_policy_dimension(r.dimension)
        if gt is None:
            continue
        if r.suppress_until is not None and r.suppress_until > as_of:
            suppressed[gt] = True
        prev = latest_fp.get(gt)
        if prev is None or r.window_start >= prev[1]:
            latest_fp[gt] = (int(r.false_positive_count), r.window_start)
    out: dict[str, tuple[int, bool]] = {}
    for gt, (fp, _) in latest_fp.items():
        out[gt] = (fp, suppressed.get(gt, False))
    return out


def fetch_gap_type_false_positive_outcome_counts_for_sort(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    window_start: datetime,
    as_of: datetime,
) -> dict[str, int]:
    """§6 Step 42 — count of outcomes with ``false_positive`` true per persisted decision ``gap_type``."""
    stmt = (
        select(ManagerInsightDecision.gap_type, func.count())
        .select_from(ManagerInsightOutcome)
        .join(ManagerInsightDecision, ManagerInsightDecision.id == ManagerInsightOutcome.decision_id)
        .where(
            ManagerInsightOutcome.tenant_id == tenant_id,
            ManagerInsightDecision.tenant_id == tenant_id,
            ManagerInsightOutcome.observed_at >= window_start,
            ManagerInsightOutcome.observed_at <= as_of,
            ManagerInsightOutcome.false_positive.is_(True),
        )
        .group_by(ManagerInsightDecision.gap_type)
    )
    return {str(gt): int(n) for gt, n in session.execute(stmt).all()}


def insert_manager_insight_policy_counter_row(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    dimension: str,
    window_start: datetime,
    false_positive_count: int = 0,
    suppress_until: datetime | None = None,
) -> ManagerInsightPolicyCounter:
    """Insert one policy counter row (integration tests / future 10.6)."""
    row = ManagerInsightPolicyCounter(
        tenant_id=tenant_id,
        dimension=dimension,
        window_start=window_start,
        false_positive_count=false_positive_count,
        suppress_until=suppress_until,
    )
    session.add(row)
    session.flush()
    return row


__all__ = [
    "ManagerInsightOutcomeListPage",
    "fetch_gap_type_false_positive_outcome_counts_for_sort",
    "fetch_gap_type_policy_for_decision_sort",
    "gap_type_from_policy_dimension",
    "get_latest_manager_insight_outcome_for_decision",
    "insert_manager_insight_outcome_row",
    "insert_manager_insight_policy_counter_row",
    "list_manager_insight_outcomes_chronological",
    "list_manager_insight_outcomes_for_tenant",
]
