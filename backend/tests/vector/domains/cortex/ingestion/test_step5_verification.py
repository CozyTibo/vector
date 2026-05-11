"""Phase 01 Step 5 — ingestion invariant verification."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.verification import verify_ingestion_run, verify_tenant_ingestion_invariants
from vector.domains.cortex.ingestion.raw_memory_contracts import verify_phase02_step1_runtime_contracts
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def test_verify_ingestion_run_not_found(db_session: Session) -> None:
    out = verify_ingestion_run(db_session, uuid.uuid4())
    assert out["passed"] is False
    assert any(c["id"] == "run_exists" and c["passed"] is False for c in out["checks"])


def test_phase02_step1_runtime_contracts_empty_scope(db_session: Session) -> None:
    out = verify_phase02_step1_runtime_contracts(db_session, uuid.uuid4())
    assert out["passed"] is True
    assert out["state"] == "unverifiable"
    ids = {c["id"] for c in out["checks"]}
    assert {
        "i1_raw_payload_immutability",
        "i2_provenance_reconstructability",
        "i3_source_identity_revision_preservation",
        "i4_replay_lineage_durability",
        "i5_deterministic_retrieval",
        "i6_temporal_ordering_determinism",
    }.issubset(ids)


def test_verify_after_successful_slack_sync(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.tenant_connection import TenantConnection
    from vector.infrastructure.db.models.user import User

    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()

    user = User(email=f"v5-{uuid.uuid4().hex[:8]}@example.com", full_name="V5 User")
    tenant = Tenant(
        company_name="VerifyCo",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"v5-{uuid.uuid4().hex[:10]}",
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

    out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tenant.id,
        connector_id="slack",
        source_trigger="test",
    )
    assert out["status"] == "completed"
    assert "verification" in out
    assert out["verification"]["passed"] is True

    sweep = verify_tenant_ingestion_invariants(db_session, tenant.id, run_limit=5)
    assert sweep["passed"] is True
    assert sweep["runs_examined"] >= 1
    assert "raw_memory_contracts" in sweep
    assert sweep["raw_memory_contracts"]["passed"] is True
    assert "raw_memory_persistence" in sweep
    assert sweep["raw_memory_persistence"]["passed"] is True
    assert "raw_memory_temporal" in sweep
    assert sweep["raw_memory_temporal"]["passed"] is True
    assert "raw_memory_replay" in sweep
    assert sweep["raw_memory_replay"]["passed"] is True
    assert "raw_memory_query" in sweep
    assert sweep["raw_memory_query"]["passed"] is True
    assert "raw_memory_storage" in sweep
    assert sweep["raw_memory_storage"]["passed"] is True
    assert "raw_memory_failure_recovery" in sweep
    assert sweep["raw_memory_failure_recovery"]["passed"] is True
    assert "raw_memory_trust" in sweep
    assert sweep["raw_memory_trust"]["passed"] is True
    assert "raw_memory_control_plane" in sweep
    assert sweep["raw_memory_control_plane"]["passed"] is True
    assert "raw_memory_phase_closure" in sweep
    assert sweep["raw_memory_phase_closure"]["phase_status"] in {"open", "closed"}
    assert "raw_memory_enforcement" in sweep
    assert sweep["raw_memory_enforcement"]["passed"] is True


def test_admin_verify_uses_session_scope(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/vector_test")
    tid = uuid.uuid4()
    from vector.api.http.routes.admin import connector_sync

    ctx = MagicMock()
    ctx.__enter__.return_value = db_session
    ctx.__exit__.return_value = None
    with patch("vector.infrastructure.db.session.session_scope", return_value=ctx):
        rep = connector_sync.verify_ingestion_invariants(tenant_id=tid, run_limit=3)
    assert rep["tenant_id"] == str(tid)
    assert "checkpoint_report" in rep
