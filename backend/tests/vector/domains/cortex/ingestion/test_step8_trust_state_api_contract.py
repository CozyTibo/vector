"""Phase 02 Step 8 — trust-state and API contract behavior."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.raw_memory_trust import (
    verify_phase02_step8_trust_api_contract,
)
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.models.raw_memory_trust_state import RawMemoryTrustState
from vector.infrastructure.db.models.raw_memory_trust_transition import RawMemoryTrustTransition
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant_with_slack(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"s8-{uuid.uuid4().hex[:8]}@example.com", full_name="Step8 User")
    tenant = Tenant(
        company_name="Step8Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"s8-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.add(
        TenantConnection(
            tenant_id=tenant.id,
            provider="slack",
            status="active",
            connected_by_user_id=user.id,
        ),
    )
    db_session.flush()
    return tenant.id, user.id


def test_step8_contract_persists_snapshot_and_transition(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    tid, _uid = _tenant_with_slack(db_session)
    out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="slack",
        source_trigger="test",
    )
    assert out["status"] == "completed"

    rep = verify_phase02_step8_trust_api_contract(
        db_session,
        tenant_id=tid,
        raw_memory_contracts={"passed": True, "state": "healthy", "checks": []},
        raw_memory_persistence={"passed": True, "state": "healthy", "checks": []},
        raw_memory_temporal={"passed": True, "state": "reconstruction-safe"},
        raw_memory_replay={
            "passed": True,
            "state": "replay-safe",
            "summary": {"highest_divergence": {"class": "D0"}},
        },
        raw_memory_query={"passed": True, "state": "healthy", "checks": []},
        raw_memory_failure_recovery={
            "passed": True,
            "summary": {"active_failure_count": 0, "active_failure_classes": {}, "latest_recovery_validation": None},
        },
    )
    assert rep["passed"] is True
    snapshot = db_session.get(RawMemoryTrustState, tid)
    assert snapshot is not None
    assert snapshot.trust_state in {"healthy", "partial", "degraded", "unverifiable"}
    transition = db_session.scalar(
        select(RawMemoryTrustTransition).where(RawMemoryTrustTransition.tenant_id == tid).limit(1)
    )
    assert transition is not None


def test_step8_contract_downgrades_with_hard_fails(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    tid = uuid.uuid4()
    db_session.add(
        Tenant(
            id=tid,
            company_name="Step8 HardFail",
            primary_email=f"step8-{uuid.uuid4().hex[:8]}@example.com",
            email_domain="example.com",
            slug=f"step8-hardfail-{uuid.uuid4().hex[:6]}",
            status="active",
            workspace_access_enabled=True,
        )
    )
    db_session.flush()
    rep = verify_phase02_step8_trust_api_contract(
        db_session,
        tenant_id=tid,
        raw_memory_contracts={"passed": True, "state": "healthy", "checks": []},
        raw_memory_persistence={"passed": False, "state": "degraded", "checks": []},
        raw_memory_temporal={"passed": False, "state": "unverifiable"},
        raw_memory_replay={
            "passed": False,
            "state": "replay-diverged",
            "summary": {"highest_divergence": {"class": "D4"}},
        },
        raw_memory_query={"passed": False, "state": "degraded", "checks": []},
        raw_memory_failure_recovery={
            "passed": False,
            "summary": {
                "active_failure_count": 1,
                "active_failure_classes": {"payload_mutation_corruption": 1},
                "latest_recovery_validation": {"status": "failed"},
            },
        },
    )
    assert rep["passed"] is True
    assert rep["state"] in {"unverifiable", "corrupted", "replay-diverged", "continuity-broken"}
