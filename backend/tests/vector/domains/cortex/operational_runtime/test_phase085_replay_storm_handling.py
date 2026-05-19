"""P085-34 — Replay storm handling (**G-P085-ECON-02**)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_replay_storm_gate import (
    verify_gp085_replay_storm_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_replay_storm_handling import (
    GP085_ECON02_GATE_ID_V1,
    REPLAY_DIVERGENCE_SOURCE_RETRIEVAL_V1,
    REPLAY_DIVERGENCE_SOURCE_SYNTHESIS_V1,
    ReplayStormHandlingError,
    activate_replay_storm_response_v1,
    assert_exploration_partition_allowed_v1,
    build_replay_storm_handling_catalog_v1,
    compute_combined_replay_divergence_rate_v1,
    evaluate_replay_storm_for_tenant_v1,
    is_saturation_blocked_by_replay_storm_v1,
    operator_acknowledge_replay_storm_v1,
    persist_replay_divergence_event_v1,
    verify_gp085_econ02_static,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling import (
    evaluate_tcre_saturation_schedule_v1,
)


def test_gp085_econ02_static_gate() -> None:
    out = verify_gp085_econ02_static()
    assert out["passed"] is True
    assert out["id"] == GP085_ECON02_GATE_ID_V1
    assert verify_gp085_replay_storm_gate_static()["passed"] is True


def test_replay_storm_catalog() -> None:
    cat = build_replay_storm_handling_catalog_v1()
    assert cat["primary_gate_id"] == GP085_ECON02_GATE_ID_V1


@pytest.mark.integration
def test_storm_activation_and_ack_flow(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085rs-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 RS",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    for _ in range(4):
        persist_replay_divergence_event_v1(
            db_session,
            tenant_id=tenant.id,
            source=REPLAY_DIVERGENCE_SOURCE_RETRIEVAL_V1,
        )
    persist_replay_divergence_event_v1(
        db_session,
        tenant_id=tenant.id,
        source=REPLAY_DIVERGENCE_SOURCE_SYNTHESIS_V1,
    )
    db_session.flush()

    rate = compute_combined_replay_divergence_rate_v1(db_session, tenant_id=tenant.id)
    assert rate["spike_detected"] is True

    control = activate_replay_storm_response_v1(
        db_session,
        tenant_id=tenant.id,
        rate_snapshot=rate,
    )
    assert control.exploration_partition_paused is True
    assert control.pinned_retrieval_policy_digest

    with pytest.raises(ReplayStormHandlingError) as exc_info:
        assert_exploration_partition_allowed_v1(db_session, tenant_id=tenant.id)
    assert exc_info.value.code == "exploration_partition_paused"

    assert is_saturation_blocked_by_replay_storm_v1(db_session, tenant_id=tenant.id) is True

    ack = operator_acknowledge_replay_storm_v1(db_session, tenant_id=tenant.id)
    assert ack["operator_acknowledged_at"] is not None
    assert is_saturation_blocked_by_replay_storm_v1(db_session, tenant_id=tenant.id) is False


@pytest.mark.integration
def test_tcre_saturation_blocked_until_ack(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085rstcre-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 RS TCRE",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    activate_replay_storm_response_v1(
        db_session,
        tenant_id=tenant.id,
        rate_snapshot={"replay_divergence_rate_per_hour": 10.0},
    )
    db_session.flush()

    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling."
        "compute_tcre_saturation_metrics_v1",
        lambda *_a, **_k: {
            "tcre_materialization_total": 10,
            "tcre_reconstructed_count": 1,
            "saturation_ratio": 0.1,
            "saturation_threshold": 0.85,
            "queued_running_jobs": 0,
            "jobs_enqueued_last_hour": 0,
            "tcre_reconstructed_count": 1,
        },
    )
    out = evaluate_tcre_saturation_schedule_v1(db_session, tenant_id=tenant.id)
    assert out["should_schedule"] is False
    assert out["schedule_reason"] == "replay_storm_operator_ack_required"


@pytest.mark.integration
def test_evaluate_card_clears_storm_when_rate_normalizes(db_session: Session) -> None:
    from vector.infrastructure.db.models.cortex_replay_storm_control import (
        CortexReplayStormControl,
    )
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085rsclear-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 RS CLR",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    control = CortexReplayStormControl(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        storm_active=True,
        exploration_partition_paused=True,
        storm_detected_at=datetime.now(tz=UTC) - timedelta(hours=2),
    )
    db_session.add(control)
    db_session.flush()

    card = evaluate_replay_storm_for_tenant_v1(db_session, tenant_id=tenant.id)
    assert card["divergence_rate"]["spike_detected"] is False
    assert card["control"]["storm_active"] is False
