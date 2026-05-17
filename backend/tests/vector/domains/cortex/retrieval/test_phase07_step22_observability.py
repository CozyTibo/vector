"""P07-22 — retrieval observability + runtime health (``retrieval.retrieval_observability``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_observability import (
    GP07_OBS01_GATE_ID_V1,
    PHASE07_RETRIEVAL_OBSERVABILITY_RUNTIME_SCHEMA_VERSION,
    build_retrieval_health_strip_v1,
    build_retrieval_observability_catalog_v1,
    build_retrieval_query_log_v1,
    build_retrieval_runtime_health_v1,
    evaluate_retrieval_alerts_v1,
    hash_retrieval_query_envelope_v1,
    persist_retrieval_query_audit_v1,
    policy_pack_observability_thresholds_v1,
    record_retrieval_legality_failure_v1,
    record_retrieval_query_observability_v1,
    snapshot_retrieval_metrics_v1,
    verify_gp07_obs01_metrics_and_health_static,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_query_audit import CortexRetrievalQueryAudit


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-observability-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_OBSERVABILITY_RUNTIME_SCHEMA_VERSION >= 1


def test_gp07_obs01_static_gate() -> None:
    out = verify_gp07_obs01_metrics_and_health_static()
    assert out["passed"] is True
    assert out["id"] == GP07_OBS01_GATE_ID_V1


def test_query_log_has_no_hit_payloads() -> None:
    log = build_retrieval_query_log_v1(
        envelope={"workload_class": "causal_chain", "intent": "inspect", "execution_partition": "authoritative"},
        result={
            "retrieval_query_replay_identity": "sha256:" + "a" * 64,
            "retrieval_legality_class": "retrieval_replay_safe",
            "hits": [{"secret": "payload"}],
            "omissions": [],
            "retrieval_query_receipt": {"receipt_digest": "sha256:" + "b" * 64},
        },
        duration_ms=5,
    )
    assert log["hit_count"] == 1
    assert "hits" not in log


def test_policy_pack_observability_thresholds() -> None:
    th = policy_pack_observability_thresholds_v1()
    assert th["completeness_critical_percent"] == 50
    assert th["replay_divergence_spike_per_hour"] == 3


def test_alert_evaluation() -> None:
    alerts = evaluate_retrieval_alerts_v1(
        health={"retrieval_completeness_percent": 10, "index_lag_epochs": 9, "recent_replay_divergences_1h": 5},
        metrics={"retrieval_queries_total": 500, "retrieval_legality_failures_total": 20},
        thresholds=policy_pack_observability_thresholds_v1(),
        tcre_jobs_present=2,
    )
    ids = {a["alert_id"] for a in alerts}
    assert "retrieval_critical" in ids
    assert "index_stale" in ids


def test_observability_catalog() -> None:
    cat = build_retrieval_observability_catalog_v1()
    assert cat["gate_id"] == GP07_OBS01_GATE_ID_V1
    assert cat["audit_table"] == "cortex_retrieval_query_audit"


def test_doctrine_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-observability-doctrine.md").read_text(
        encoding="utf-8"
    )
    assert "build_retrieval_runtime_health_v1" in text


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7obs-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Obs")
    tenant = Tenant(
        company_name="P7OBS",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7obs-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_runtime_health_and_audit_on_query(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=replay,
        traversal_epoch=epoch,
    )
    db_session.commit()
    before_metrics = snapshot_retrieval_metrics_v1()["retrieval_queries_total"]
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "workload_class": "causal_chain",
            "intent": "inspect",
            "addressing": {"retrieval_lookup_id": row.retrieval_lookup_id},
            "replay_pins": {
                "index_epoch": epoch,
                "tcre_policy_bundle_digest": "sha256:policy-stub",
                "octs_engine_build_ref": "build-stub",
            },
            "expected_replay_identity": replay,
            "selection_policy": {"max_hits": 50},
        },
    )
    db_session.commit()
    assert isinstance(out.get("retrieval_query_log"), dict)
    after_metrics = snapshot_retrieval_metrics_v1()["retrieval_queries_total"]
    assert after_metrics >= before_metrics + 1
    audits = db_session.scalars(
        select(CortexRetrievalQueryAudit).where(CortexRetrievalQueryAudit.tenant_id == tenant_id)
    ).all()
    assert len(audits) >= 1
    assert audits[-1].receipt_digest
    health = build_retrieval_runtime_health_v1(db_session, tenant_id=tenant_id)
    assert health.get("substrate_state") is not None
    assert "r_leg_health" in health
    strip = build_retrieval_health_strip_v1(db_session, tenant_id=tenant_id)
    assert "active_alerts" in strip


@pytest.mark.integration
def test_persist_audit_direct(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    envelope = {
        "workload_class": "causal_chain",
        "intent": "inspect",
        "execution_partition": "authoritative",
        "addressing": {"causal_chain_id": "c-direct"},
    }
    result = {
        "retrieval_legality_class": "retrieval_replay_safe",
        "retrieval_query_replay_identity": "sha256:" + "c" * 64,
        "hits": [],
        "omissions": [],
        "retrieval_query_receipt": {"receipt_digest": "sha256:" + "d" * 64},
    }
    row = persist_retrieval_query_audit_v1(
        db_session,
        tenant_id=tenant_id,
        envelope=envelope,
        result=result,
        duration_ms=7,
    )
    db_session.commit()
    assert row.query_envelope_hash == hash_retrieval_query_envelope_v1(envelope)
    obs = record_retrieval_query_observability_v1(
        db_session,
        tenant_id=tenant_id,
        envelope=envelope,
        result=result,
        duration_ms=8,
    )
    assert obs.get("audit_id")
    record_retrieval_legality_failure_v1(reason="test_forbidden")
