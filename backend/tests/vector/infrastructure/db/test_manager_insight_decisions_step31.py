"""§6 Step 31 — ORM mapping + insert_decisions_bulk (unit, no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from vector.contracts.manager_insights_activity import DecisionDefaultAction, DecisionItem
from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision
from vector.infrastructure.db.repositories import manager_insight_decisions as mid_repo


def _item(*, did: str, tenant_run: uuid.UUID) -> DecisionItem:
    return DecisionItem(
        id=did,
        gap_id="g1",
        gap_type="blocker_not_tracked",
        decision_type="BLOCKER_ESCALATION",
        title="t",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={},
        evidence_refs=["e1"],
        signal_refs=["s1"],
        created_at=datetime(2026, 4, 1, tzinfo=UTC),
        run_id=tenant_run,
        status="proposed",
    )


def test_manager_insight_decision_id_is_stable_per_tenant_and_engine_id() -> None:
    tid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    a = mid_repo.manager_insight_decision_id_for_engine_row(tenant_id=tid, engine_decision_id="coordination:decision:x")
    b = mid_repo.manager_insight_decision_id_for_engine_row(tenant_id=tid, engine_decision_id="coordination:decision:x")
    c = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        engine_decision_id="coordination:decision:x",
    )
    assert a == b
    assert a != c


def test_manager_insight_decision_from_item_maps_json_and_arrays() -> None:
    rid = uuid.UUID("11111111-2222-3333-4444-555555555555")
    tid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    item = _item(did="coordination:decision:unit", tenant_run=rid)
    row = mid_repo.manager_insight_decision_from_item(tenant_id=tid, item=item, rank=2)
    assert row.id == mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=tid,
        engine_decision_id=item.id,
    )
    assert row.tenant_id == tid
    assert row.run_id == rid
    assert row.gap_id == "g1"
    assert row.rank == 2
    assert row.default_action == {"kind": "noop", "connector": None, "payload_template": {}}
    assert row.evidence_refs == ["e1"]
    assert row.signal_refs == ["s1"]
    assert row.status == "proposed"


def test_decision_items_to_rows_requires_matching_ranks_len() -> None:
    tid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    rid = uuid.UUID("11111111-2222-3333-4444-555555555555")
    items = [_item(did="a", tenant_run=rid), _item(did="b", tenant_run=rid)]
    with pytest.raises(ValueError, match="ranks length"):
        mid_repo.decision_items_to_manager_insight_rows(tenant_id=tid, items=items, ranks=[1])


def test_decision_items_to_rows_sets_ranks() -> None:
    tid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    rid = uuid.UUID("11111111-2222-3333-4444-555555555555")
    items = [
        _item(did="coordination:decision:one", tenant_run=rid),
        _item(did="coordination:decision:two", tenant_run=rid),
    ]
    rows = mid_repo.decision_items_to_manager_insight_rows(tenant_id=tid, items=items, ranks=[1, 2])
    assert rows[0].rank == 1
    assert rows[1].rank == 2


def test_insert_decisions_bulk_adds_all() -> None:
    session = MagicMock()
    tid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    rid = uuid.UUID("11111111-2222-3333-4444-555555555555")
    r1 = mid_repo.manager_insight_decision_from_item(
        tenant_id=tid,
        item=_item(did="x", tenant_run=rid),
    )
    r2 = mid_repo.manager_insight_decision_from_item(
        tenant_id=tid,
        item=_item(did="y", tenant_run=rid),
    )
    n = mid_repo.insert_decisions_bulk(session, [r1, r2])
    assert n == 2
    session.add_all.assert_called_once()
    session.flush.assert_called_once()


def test_insert_decision_items_bulk_delegates() -> None:
    session = MagicMock()
    tid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    rid = uuid.UUID("11111111-2222-3333-4444-555555555555")
    items = [_item(did="coordination:decision:a", tenant_run=rid)]
    n = mid_repo.insert_decision_items_bulk(session, tenant_id=tid, items=items)
    assert n == 1
    session.add_all.assert_called_once()
    args, _ = session.add_all.call_args
    assert len(args[0]) == 1
    assert isinstance(args[0][0], ManagerInsightDecision)
