"""Operator admin v2 routes (R2 runtime + unified actions)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.pipeline.operator_admin_actions import (
    CORTEX_CLEAR_DERIVED_CONFIRM_PHRASE,
    CORTEX_RESTART_EXECUTION_CONFIRM_PHRASE,
    CONTINUITY_P0_RECOVER_CONFIRM_PHRASE,
)
from vector.domains.cortex.pipeline.pipeline_admin_run import CORTEX_MANUAL_SYNC_CONFIRM_PHRASE
from vector.domains.cortex.retrieval.retrieval_operator_workflows import (
    RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"opr2-{uuid.uuid4().hex[:10]}@example.com", full_name="Op R2")
    tenant = Tenant(
        company_name="Op R2 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"opr2-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_operator_runtime(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.get(
        f"/admin/tenants/{tid}/cortex/operator/runtime",
        params={"transition_limit": 10, "transition_offset": 0},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_runtime_v1"
    assert body["tenant_id"] == str(tid)
    assert body["transition_limit"] == 10
    assert body["transition_offset"] == 0
    assert "dual_lane" in body
    assert "queue_counts" in body
    assert "island_registry" not in body
    assert "per_island_synthesis" not in body


def test_operator_action_run_from_phase(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.post(
        f"/admin/tenants/{tid}/cortex/operator/actions",
        json={"action": "run_from_phase", "start_phase": "canonical"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["surface_kind"] == "operator_action_v1"
    assert body["action"] == "run_from_phase"
    assert body["tenant_id"] == str(tid)


def test_operator_action_confirmation_mismatch(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    res = client.post(
        f"/admin/tenants/{tid}/cortex/operator/actions",
        json={"action": "run_from_ingestion", "confirmation": "wrong"},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Confirmation phrase does not match."


def test_operator_action_restart_requires_confirmation(
    client: TestClient,
    db_session: Session,
) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    bad = client.post(
        f"/admin/tenants/{tid}/cortex/operator/actions",
        json={"action": "restart_execution", "start_phase": "identity"},
    )
    assert bad.status_code == 400

    ok = client.post(
        f"/admin/tenants/{tid}/cortex/operator/actions",
        json={
            "action": "restart_execution",
            "start_phase": "identity",
            "confirmation": CORTEX_RESTART_EXECUTION_CONFIRM_PHRASE,
        },
    )
    assert ok.status_code == 200
    assert ok.json()["action"] == "restart_execution"


def test_operator_action_phrases_exported(
    client: TestClient,
    db_session: Session,
) -> None:
    """Smoke: confirmation-gated actions accept canonical phrases (no 400 mismatch)."""
    tid = _tenant(db_session)
    db_session.commit()

    ingestion = client.post(
        f"/admin/tenants/{tid}/cortex/operator/actions",
        json={"action": "run_from_ingestion", "confirmation": CORTEX_MANUAL_SYNC_CONFIRM_PHRASE},
    )
    assert ingestion.status_code == 200

    clear = client.post(
        f"/admin/tenants/{tid}/cortex/operator/actions",
        json={
            "action": "clear_derived",
            "start_phase": "canonical",
            "confirmation": CORTEX_CLEAR_DERIVED_CONFIRM_PHRASE,
        },
    )
    assert clear.status_code == 200

    rebuild = client.post(
        f"/admin/tenants/{tid}/cortex/operator/actions",
        json={
            "action": "rebuild_retrieval_index",
            "confirmation": RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1,
        },
    )
    assert rebuild.status_code == 200

    identities = client.post(
        f"/admin/tenants/{tid}/cortex/operator/actions",
        json={
            "action": "rebuild_identities",
            "confirmation": "REBUILD IDENTITIES FROM CANONICAL ANCHORS",
        },
    )
    assert identities.status_code == 200
    assert identities.json()["action"] == "rebuild_identities"

    p0 = client.post(
        f"/admin/tenants/{tid}/cortex/operator/actions",
        json={"action": "p0_recover", "confirmation": CONTINUITY_P0_RECOVER_CONFIRM_PHRASE},
    )
    assert p0.status_code in (200, 409)
