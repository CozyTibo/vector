"""§6 Step 31 — persist ``DecisionItem`` rows to ``manager_insight_decisions``."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from vector.contracts.manager_insights_activity import DecisionItem
from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision


def manager_insight_decision_id_for_engine_row(*, tenant_id: uuid.UUID, engine_decision_id: str) -> uuid.UUID:
    """Deterministic UUID PK from tenant + engine ``DecisionItem.id`` (string)."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"{tenant_id}:{engine_decision_id}")


def manager_insight_decision_from_item(
    *,
    tenant_id: uuid.UUID,
    item: DecisionItem,
    rank: int | None = None,
    idempotency_key: str | None = None,
) -> ManagerInsightDecision:
    """Map a coordination ``DecisionItem`` to a new ORM instance (not yet flushed)."""
    row_id = manager_insight_decision_id_for_engine_row(tenant_id=tenant_id, engine_decision_id=item.id)
    status = item.status if item.status is not None else "proposed"
    return ManagerInsightDecision(
        id=row_id,
        tenant_id=tenant_id,
        run_id=item.run_id,
        gap_id=item.gap_id,
        gap_type=item.gap_type,
        decision_type=item.decision_type,
        title=item.title,
        rationale=item.rationale,
        default_action=item.default_action.model_dump(mode="json"),
        required_inputs=dict(item.required_inputs),
        evidence_refs=list(item.evidence_refs),
        signal_refs=list(item.signal_refs),
        status=status,
        rank=rank,
        idempotency_key=idempotency_key,
        slack_channel_id=None,
        slack_message_ts=None,
        receipt=None,
    )


def decision_items_to_manager_insight_rows(
    *,
    tenant_id: uuid.UUID,
    items: Sequence[DecisionItem],
    ranks: Sequence[int | None] | None = None,
) -> list[ManagerInsightDecision]:
    """Zip ``DecisionItem`` rows with optional per-row ``rank`` (1-based surface order)."""
    if ranks is not None and len(ranks) != len(items):
        msg = "ranks length must match items"
        raise ValueError(msg)
    out: list[ManagerInsightDecision] = []
    for i, item in enumerate(items):
        r = ranks[i] if ranks is not None else None
        out.append(
            manager_insight_decision_from_item(
                tenant_id=tenant_id,
                item=item,
                rank=r,
            )
        )
    return out


def insert_decisions_bulk(session: Session, rows: Sequence[ManagerInsightDecision]) -> int:
    """Insert coordination decision rows in one batch. Does not commit.

    Returns the number of rows added.
    """
    rows_list = list(rows)
    if not rows_list:
        return 0
    session.add_all(rows_list)
    session.flush()
    return len(rows_list)


def insert_decision_items_bulk(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    items: Sequence[DecisionItem],
    ranks: Sequence[int | None] | None = None,
) -> int:
    """Convenience: map ``DecisionItem`` → ORM and ``insert_decisions_bulk``."""
    orm_rows = decision_items_to_manager_insight_rows(
        tenant_id=tenant_id,
        items=items,
        ranks=ranks,
    )
    return insert_decisions_bulk(session, orm_rows)


def _manager_insight_decision_insert_mapping(row: ManagerInsightDecision) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "run_id": row.run_id,
        "gap_id": row.gap_id,
        "gap_type": row.gap_type,
        "decision_type": row.decision_type,
        "title": row.title,
        "rationale": row.rationale,
        "default_action": row.default_action,
        "required_inputs": row.required_inputs,
        "evidence_refs": row.evidence_refs,
        "signal_refs": row.signal_refs,
        "status": row.status,
        "rank": row.rank,
        "slack_channel_id": row.slack_channel_id,
        "slack_message_ts": row.slack_message_ts,
        "idempotency_key": row.idempotency_key,
        "receipt": row.receipt,
    }


def upsert_decision_items_bulk(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    items: Sequence[DecisionItem],
    ranks: Sequence[int | None] | None = None,
) -> int:
    """Insert or update rows by primary key (``id``). Preserves Slack / ``receipt`` / ``idempotency_key`` when omitted.

    §6 Step 32 — idempotent re-runs of fetch-debug persist for the same engine decision id.
    """
    orm_rows = decision_items_to_manager_insight_rows(
        tenant_id=tenant_id,
        items=items,
        ranks=ranks,
    )
    if not orm_rows:
        return 0
    table = ManagerInsightDecision.__table__
    n = 0
    for row in orm_rows:
        m = _manager_insight_decision_insert_mapping(row)
        ins = pg_insert(table).values(m)
        ex = ins.excluded
        stmt = ins.on_conflict_do_update(
            index_elements=[table.c.id],
            set_={
                "tenant_id": ex.tenant_id,
                "run_id": ex.run_id,
                "gap_id": ex.gap_id,
                "gap_type": ex.gap_type,
                "decision_type": ex.decision_type,
                "title": ex.title,
                "rationale": ex.rationale,
                "default_action": ex.default_action,
                "required_inputs": ex.required_inputs,
                "evidence_refs": ex.evidence_refs,
                "signal_refs": ex.signal_refs,
                "status": ex.status,
                "rank": ex.rank,
                "updated_at": func.now(),
            },
        )
        session.execute(stmt)
        n += 1
    return n


@dataclass(frozen=True, slots=True)
class ManagerInsightDecisionListPage:
    """§6 Step 33 — one page of persisted rows + total count for pagination."""

    items: list[ManagerInsightDecision]
    total: int


def list_manager_insight_decisions_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
    status: str | None = None,
    decision_type: str | None = None,
    gap_type: str | None = None,
    gap_id: str | None = None,
    run_id: uuid.UUID | None = None,
) -> ManagerInsightDecisionListPage:
    """List persisted coordination decisions for a tenant (newest ``updated_at`` first).

    Optional ``gap_id`` (§6 Step 34) filters to a single coordination gap key.
    """
    clauses: list[Any] = [ManagerInsightDecision.tenant_id == tenant_id]
    if status is not None:
        clauses.append(ManagerInsightDecision.status == status)
    if decision_type is not None:
        clauses.append(ManagerInsightDecision.decision_type == decision_type)
    if gap_type is not None:
        clauses.append(ManagerInsightDecision.gap_type == gap_type)
    if gap_id is not None:
        clauses.append(ManagerInsightDecision.gap_id == gap_id)
    if run_id is not None:
        clauses.append(ManagerInsightDecision.run_id == run_id)
    where_clause = and_(*clauses)

    total = session.scalar(
        select(func.count()).select_from(ManagerInsightDecision).where(where_clause),
    )
    if total is None:
        total = 0

    stmt = (
        select(ManagerInsightDecision)
        .where(where_clause)
        .order_by(ManagerInsightDecision.updated_at.desc(), ManagerInsightDecision.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = list(session.scalars(stmt).all())
    return ManagerInsightDecisionListPage(items=rows, total=total)


def get_manager_insight_decision_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    decision_id: uuid.UUID,
) -> ManagerInsightDecision | None:
    """Return one persisted row if it belongs to ``tenant_id``."""
    return session.scalar(
        select(ManagerInsightDecision).where(
            ManagerInsightDecision.id == decision_id,
            ManagerInsightDecision.tenant_id == tenant_id,
        ),
    )


__all__ = [
    "ManagerInsightDecisionListPage",
    "decision_items_to_manager_insight_rows",
    "get_manager_insight_decision_for_tenant",
    "insert_decision_items_bulk",
    "insert_decisions_bulk",
    "list_manager_insight_decisions_for_tenant",
    "manager_insight_decision_from_item",
    "manager_insight_decision_id_for_engine_row",
    "upsert_decision_items_bulk",
]
