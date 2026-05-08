"""Phase 02 Step 13 — replay divergence proof matrix + forbidden denial paths."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.raw_memory_phase_closure import (
    evaluate_phase02_step10_closure_gate,
)
from vector.domains.cortex.ingestion.raw_memory_replay import (
    FORBIDDEN_DIVERGENCE_CLASSES,
    REPLAY_DIVERGENCE_CLASS_IDS,
    verify_phase02_step4_replay_equivalence,
)
from vector.domains.cortex.ingestion.raw_memory_replay_hardening import (
    verify_phase02_step13_replay_divergence_hardening,
)
from vector.domains.cortex.ingestion.raw_memory_verification_unified import (
    compute_phase02_gates_g1_g7,
)
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_executor import _append_raw
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_memory_failure_case import RawMemoryFailureCase
from vector.infrastructure.db.models.tenant_connection import TenantConnection


def _tenant_with_slack(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"s13-{uuid.uuid4().hex[:8]}@example.com", full_name="Step13 User")
    tenant = Tenant(
        company_name="Step13Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"s13-{uuid.uuid4().hex[:10]}",
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


def test_step13_divergence_registry_covers_d0_d5() -> None:
    assert REPLAY_DIVERGENCE_CLASS_IDS == ("D0", "D1", "D2", "D3", "D4", "D5")
    assert FORBIDDEN_DIVERGENCE_CLASSES == frozenset({"D3", "D4", "D5"})


def test_step13_hardening_passes_on_valid_step4_shape() -> None:
    rep = {
        "passed": True,
        "state": "replay-safe",
        "summary": {"highest_divergence": {"class": "D0"}},
        "jobs": [
            {
                "replay_job_id": str(uuid.uuid4()),
                "highest_divergence": {"class": "D0"},
                "blocking": False,
                "class_counts": {"D0": 1, "D1": 0, "D2": 0, "D3": 0, "D4": 0, "D5": 0},
            }
        ],
    }
    hard = verify_phase02_step13_replay_divergence_hardening(rep)
    assert hard["passed"] is True


def test_step13_forbidden_requires_blocking_job() -> None:
    bad = {
        "passed": False,
        "state": "replay-diverged",
        "summary": {"highest_divergence": {"class": "D3"}},
        "jobs": [{"highest_divergence": {"class": "D3"}, "blocking": False}],
    }
    assert verify_phase02_step13_replay_divergence_hardening(bad)["passed"] is False


def test_step13_forbidden_aggregate_must_fail_pass_bit() -> None:
    bad = {
        "passed": True,
        "state": "replay-diverged",
        "summary": {"highest_divergence": {"class": "D4"}},
        "jobs": [],
    }
    assert verify_phase02_step13_replay_divergence_hardening(bad)["passed"] is False


def test_step13_acceptable_classes_must_not_block() -> None:
    bad = {
        "passed": True,
        "state": "partial",
        "summary": {"highest_divergence": {"class": "D1"}},
        "jobs": [{"highest_divergence": {"class": "D1"}, "blocking": True}],
    }
    assert verify_phase02_step13_replay_divergence_hardening(bad)["passed"] is False


@pytest.mark.integration
def test_step13_closure_merges_g13_when_hardening_passes(db_session: Session) -> None:
    tid, _uid = _tenant_with_slack(db_session)
    hard = verify_phase02_step13_replay_divergence_hardening(
        {
            "passed": True,
            "state": "replay-safe",
            "summary": {"highest_divergence": {"class": "D0"}},
            "jobs": [],
        }
    )
    fr_min = {"passed": True, "summary": {"active_failure_classes": {}}, "checks": []}
    g17 = compute_phase02_gates_g1_g7(
        raw_memory_contracts={"passed": True},
        raw_memory_persistence={"passed": True},
        raw_memory_temporal={"passed": True, "state": "reconstruction-safe"},
        raw_memory_replay={"passed": True, "summary": {"highest_divergence": {"class": "D0"}}},
        raw_memory_query={"passed": True},
        raw_memory_failure_recovery=fr_min,
    )
    closure = evaluate_phase02_step10_closure_gate(
        tenant_id=tid,
        raw_memory_contracts={"passed": True},
        raw_memory_persistence={"passed": True},
        raw_memory_temporal={"passed": True, "state": "reconstruction-safe"},
        raw_memory_replay={
            "passed": True,
            "summary": {"highest_divergence": {"class": "D0"}},
        },
        raw_memory_query={"passed": True},
        raw_memory_failure_recovery=fr_min,
        raw_memory_trust={
            "passed": True,
            "checks": [{"id": "s8_deterministic_transition_logic", "passed": True}],
        },
        raw_memory_control_plane={"passed": True},
        control_plane_payload={
            "warnings": {
                "must_not_assume": [
                    "replay-safe does not imply replay-complete provider omniscience",
                ]
            }
        },
        precomputed_gates_g1_g7=g17,
        raw_memory_replay_hardening=hard,
    )
    assert closure["gate_results"]["G13"]["decision"] == "pass"


@pytest.mark.integration
def test_step13_matrix_d3_duplicate_replay_logical_keys(db_session: Session) -> None:
    tid, _uid = _tenant_with_slack(db_session)
    conn_id = db_session.scalar(
        select(TenantConnection.id).where(
            TenantConnection.tenant_id == tid,
            TenantConnection.provider == "slack",
        )
    )
    assert conn_id is not None

    live_run_id = uuid.uuid4()
    replay_run_id = uuid.uuid4()
    replay_job_id = uuid.uuid4()
    db_session.add_all(
        [
            IngestionRun(
                id=live_run_id,
                tenant_id=tid,
                connection_id=conn_id,
                connector="slack",
                source_trigger="test",
                sync_mode="incremental",
                replay_mode=False,
                replay_version=1,
                status="RUNNING",
                started_at=datetime.now(tz=UTC),
            ),
            IngestionRun(
                id=replay_run_id,
                tenant_id=tid,
                connection_id=conn_id,
                connector="slack",
                source_trigger="replay",
                sync_mode="replay",
                replay_mode=True,
                replay_job_id=replay_job_id,
                replay_version=1,
                status="RUNNING",
                started_at=datetime.now(tz=UTC),
            ),
        ]
    )
    db_session.flush()

    env = core_envelope_fields(
        connector="slack",
        connection_id=conn_id,
        source_object_type="slack.message",
        source_object_id="msg-dup",
    )
    body = {**env, "updated_at": "2026-01-01T00:00:10+00:00", "text": "x"}
    assert _append_raw(
        db_session,
        ctx=IngestionSyncContext.live_incremental(),
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=live_run_id,
        source_trigger="live",
        resource_type="slack.message",
        external_id="msg-dup",
        api_endpoint="internal://test/live",
        query_params={},
        payload_body=body,
        http_status=200,
        idempotency_key="live-dup",
    )
    for i in range(2):
        assert _append_raw(
            db_session,
            ctx=IngestionSyncContext.replay(replay_job_id=replay_job_id),
            tenant_id=tid,
            connection_id=conn_id,
            connector="slack",
            run_id=replay_run_id,
            source_trigger="replay",
            resource_type="slack.message",
            external_id="msg-dup",
            api_endpoint="internal://test/replay",
            query_params={},
            payload_body=body,
            http_status=200,
            idempotency_key=f"replay-dup-{i}",
        )

    rep = verify_phase02_step4_replay_equivalence(db_session, tid)
    assert rep["summary"]["highest_divergence"]["class"] == "D3"
    assert rep["passed"] is False
    hard = verify_phase02_step13_replay_divergence_hardening(rep)
    assert hard["passed"] is True


@pytest.mark.integration
def test_step13_matrix_d4_lineage_break_no_live_match(db_session: Session) -> None:
    tid, _uid = _tenant_with_slack(db_session)
    conn_id = db_session.scalar(
        select(TenantConnection.id).where(
            TenantConnection.tenant_id == tid,
            TenantConnection.provider == "slack",
        )
    )
    assert conn_id is not None

    live_run_id = uuid.uuid4()
    replay_run_id = uuid.uuid4()
    replay_job_id = uuid.uuid4()
    db_session.add_all(
        [
            IngestionRun(
                id=live_run_id,
                tenant_id=tid,
                connection_id=conn_id,
                connector="slack",
                source_trigger="test",
                sync_mode="incremental",
                replay_mode=False,
                replay_version=1,
                status="RUNNING",
                started_at=datetime.now(tz=UTC),
            ),
            IngestionRun(
                id=replay_run_id,
                tenant_id=tid,
                connection_id=conn_id,
                connector="slack",
                source_trigger="replay",
                sync_mode="replay",
                replay_mode=True,
                replay_job_id=replay_job_id,
                replay_version=1,
                status="RUNNING",
                started_at=datetime.now(tz=UTC),
            ),
        ]
    )
    db_session.flush()

    env_anchor = core_envelope_fields(
        connector="slack",
        connection_id=conn_id,
        source_object_type="slack.message",
        source_object_id="msg-anchor",
    )
    anchor_body = {**env_anchor, "updated_at": "2026-01-01T00:00:10+00:00", "text": "anchor"}
    assert _append_raw(
        db_session,
        ctx=IngestionSyncContext.live_incremental(),
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=live_run_id,
        source_trigger="live",
        resource_type="slack.message",
        external_id="msg-anchor",
        api_endpoint="internal://test/live",
        query_params={},
        payload_body=anchor_body,
        http_status=200,
        idempotency_key="live-anchor",
    )

    env_orphan = core_envelope_fields(
        connector="slack",
        connection_id=conn_id,
        source_object_type="slack.message",
        source_object_id="msg-orphan",
    )
    orphan_body = {**env_orphan, "updated_at": "2026-01-01T00:00:10+00:00", "text": "orphan"}
    assert _append_raw(
        db_session,
        ctx=IngestionSyncContext.replay(replay_job_id=replay_job_id),
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=replay_run_id,
        source_trigger="replay",
        resource_type="slack.message",
        external_id="msg-orphan",
        api_endpoint="internal://test/replay",
        query_params={},
        payload_body=orphan_body,
        http_status=200,
        idempotency_key="replay-orphan",
    )

    rep = verify_phase02_step4_replay_equivalence(db_session, tid)
    assert rep["summary"]["highest_divergence"]["class"] == "D4"
    assert rep["passed"] is False
    assert verify_phase02_step13_replay_divergence_hardening(rep)["passed"] is True


@pytest.mark.integration
def test_step13_matrix_d5_when_continuity_broken_and_d4_replay(db_session: Session) -> None:
    tid, _uid = _tenant_with_slack(db_session)
    conn_id = db_session.scalar(
        select(TenantConnection.id).where(
            TenantConnection.tenant_id == tid,
            TenantConnection.provider == "slack",
        )
    )
    assert conn_id is not None

    gid = hashlib.sha256(f"lineage|{tid}|test".encode()).hexdigest()[:64]
    db_session.add(
        RawMemoryFailureCase(
            gap_id=gid,
            tenant_id=tid,
            failure_class="lineage_discontinuity",
            gap_type="lineage_break_window",
            scope_connector="slack",
            scope_resource_type="slack.message",
            scope_source_identity_key="scope-k",
            source="integrity_scan",
            trust_state_impact="continuity-broken",
            recoverability_class="recoverable",
            recovery_status="pending",
            active=True,
            detail={},
        )
    )

    live_run_id = uuid.uuid4()
    replay_run_id = uuid.uuid4()
    replay_job_id = uuid.uuid4()
    db_session.add_all(
        [
            IngestionRun(
                id=live_run_id,
                tenant_id=tid,
                connection_id=conn_id,
                connector="slack",
                source_trigger="test",
                sync_mode="incremental",
                replay_mode=False,
                replay_version=1,
                status="RUNNING",
                started_at=datetime.now(tz=UTC),
            ),
            IngestionRun(
                id=replay_run_id,
                tenant_id=tid,
                connection_id=conn_id,
                connector="slack",
                source_trigger="replay",
                sync_mode="replay",
                replay_mode=True,
                replay_job_id=replay_job_id,
                replay_version=1,
                status="RUNNING",
                started_at=datetime.now(tz=UTC),
            ),
        ]
    )
    db_session.flush()

    env_anchor = core_envelope_fields(
        connector="slack",
        connection_id=conn_id,
        source_object_type="slack.message",
        source_object_id="msg-a2",
    )
    anchor_body = {**env_anchor, "updated_at": "2026-01-01T00:00:10+00:00", "text": "anchor"}
    assert _append_raw(
        db_session,
        ctx=IngestionSyncContext.live_incremental(),
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=live_run_id,
        source_trigger="live",
        resource_type="slack.message",
        external_id="msg-a2",
        api_endpoint="internal://test/live",
        query_params={},
        payload_body=anchor_body,
        http_status=200,
        idempotency_key="live-a2",
    )

    env_orphan = core_envelope_fields(
        connector="slack",
        connection_id=conn_id,
        source_object_type="slack.message",
        source_object_id="msg-o2",
    )
    orphan_body = {**env_orphan, "updated_at": "2026-01-01T00:00:10+00:00", "text": "orphan"}
    assert _append_raw(
        db_session,
        ctx=IngestionSyncContext.replay(replay_job_id=replay_job_id),
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=replay_run_id,
        source_trigger="replay",
        resource_type="slack.message",
        external_id="msg-o2",
        api_endpoint="internal://test/replay",
        query_params={},
        payload_body=orphan_body,
        http_status=200,
        idempotency_key="replay-o2",
    )

    rep = verify_phase02_step4_replay_equivalence(db_session, tid)
    assert rep["summary"]["highest_divergence"]["class"] == "D5"
    assert rep["passed"] is False
    assert verify_phase02_step13_replay_divergence_hardening(rep)["passed"] is True


@pytest.mark.integration
def test_step13_matrix_d2_schema_reinterpretation(db_session: Session) -> None:
    tid, _uid = _tenant_with_slack(db_session)
    conn_id = db_session.scalar(
        select(TenantConnection.id).where(
            TenantConnection.tenant_id == tid,
            TenantConnection.provider == "slack",
        )
    )
    assert conn_id is not None

    live_run_id = uuid.uuid4()
    replay_run_id = uuid.uuid4()
    replay_job_id = uuid.uuid4()
    db_session.add_all(
        [
            IngestionRun(
                id=live_run_id,
                tenant_id=tid,
                connection_id=conn_id,
                connector="slack",
                source_trigger="test",
                sync_mode="incremental",
                replay_mode=False,
                replay_version=1,
                status="RUNNING",
                started_at=datetime.now(tz=UTC),
            ),
            IngestionRun(
                id=replay_run_id,
                tenant_id=tid,
                connection_id=conn_id,
                connector="slack",
                source_trigger="replay",
                sync_mode="replay",
                replay_mode=True,
                replay_job_id=replay_job_id,
                replay_version=1,
                status="RUNNING",
                started_at=datetime.now(tz=UTC),
            ),
        ]
    )
    db_session.flush()

    env = core_envelope_fields(
        connector="slack",
        connection_id=conn_id,
        source_object_type="slack.message",
        source_object_id="msg-sch",
    )
    live_body = {
        **env,
        "updated_at": "2026-01-01T00:00:10+00:00",
        "text": "x",
        "ingestion_version": {"schema": "a"},
    }
    replay_body = {
        **env,
        "updated_at": "2026-01-01T00:00:10+00:00",
        "text": "x",
        "ingestion_version": {"schema": "b"},
    }
    assert _append_raw(
        db_session,
        ctx=IngestionSyncContext.live_incremental(),
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=live_run_id,
        source_trigger="live",
        resource_type="slack.message",
        external_id="msg-sch",
        api_endpoint="internal://test/live",
        query_params={},
        payload_body=live_body,
        http_status=200,
        idempotency_key="live-sch",
    )
    assert _append_raw(
        db_session,
        ctx=IngestionSyncContext.replay(replay_job_id=replay_job_id),
        tenant_id=tid,
        connection_id=conn_id,
        connector="slack",
        run_id=replay_run_id,
        source_trigger="replay",
        resource_type="slack.message",
        external_id="msg-sch",
        api_endpoint="internal://test/replay",
        query_params={},
        payload_body=replay_body,
        http_status=200,
        idempotency_key="replay-sch",
    )

    rep = verify_phase02_step4_replay_equivalence(db_session, tid)
    assert rep["summary"]["highest_divergence"]["class"] == "D2"
    assert rep["passed"] is True
    assert verify_phase02_step13_replay_divergence_hardening(rep)["passed"] is True
