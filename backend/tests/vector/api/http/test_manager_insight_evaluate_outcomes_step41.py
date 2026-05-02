"""§6 Step 41 — POST /admin/tenants/{id}/manager-insight/evaluate-outcomes (integration)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.contracts.manager_insights_activity import DecisionDefaultAction, DecisionItem
from vector.domains.manager_insights.evaluate_outcomes import RULE_VERSION
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import manager_insight_decisions as mid_repo
from vector.infrastructure.db.repositories import manager_insight_outcomes as mio_repo
from vector.settings import get_settings


@pytest.mark.integration
def test_evaluate_outcomes_merges_ground_truth_and_skips_idempotent(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "step41-admin-test-password")
    get_settings.cache_clear()

    tenant = Tenant(
        company_name="Step41 Co",
        primary_email="s41@example.com",
        email_domain="example.com",
        slug=f"s41-{uuid.uuid4().hex[:12]}",
        status="active",
    )
    db_session.add(tenant)
    db_session.flush()

    run_id = uuid.uuid4()
    item = DecisionItem(
        id="engine:decision:step41-eval",
        gap_id="gap-e",
        gap_type="expected_not_executed",
        decision_type="LINK_OR_CLOSE_COMMITMENT",
        title="Eval parent",
        rationale="r",
        default_action=DecisionDefaultAction(kind="noop"),
        required_inputs={},
        evidence_refs=[],
        signal_refs=[],
        created_at=datetime(2026, 5, 5, 10, 0, 0, tzinfo=UTC),
        run_id=run_id,
        status="dismissed",
    )
    mid_repo.insert_decision_items_bulk(db_session, tenant_id=tenant.id, items=[item], ranks=[1])
    db_session.flush()
    pk = mid_repo.manager_insight_decision_id_for_engine_row(
        tenant_id=tenant.id,
        engine_decision_id=item.id,
    )
    mio_repo.insert_manager_insight_outcome_row(
        db_session,
        tenant_id=tenant.id,
        decision_id=pk,
        outcome_type="dismissed",
        observed_at=datetime(2026, 5, 5, 11, 0, 0, tzinfo=UTC),
    )
    db_session.flush()

    auth = ("x", "step41-admin-test-password")
    url = f"/admin/tenants/{tenant.id}/manager-insight/evaluate-outcomes"

    r1 = client.post(url, auth=auth, json={"limit": 10, "reset": False})
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["processed"] == 1
    assert b1["skipped"] == 0
    assert b1["scanned"] == 1
    assert b1["items"][0]["ground_truth_after"]["rule_version"] == RULE_VERSION
    assert b1["items"][0]["ground_truth_after"]["decision_outcome_coherent"] is True

    r2 = client.post(url, auth=auth, json={"limit": 10, "reset": False})
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["processed"] == 0
    assert b2["skipped"] == 1
    assert b2["scanned"] == 1

    r3 = client.post(url, auth=auth, json={"limit": 10, "reset": True})
    assert r3.status_code == 200
    assert r3.json()["processed"] == 1
