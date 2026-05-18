"""Phase 08 Step 21 — synthesis observability + runtime health."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_bounded_caps import reset_synthesis_omission_histogram_v1
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_observability import (
    GP08_OBS01_GATE_ID_V1,
    PHASE08_SYNTHESIS_OBSERVABILITY_RUNTIME_SCHEMA_VERSION,
    build_synthesis_health_strip_v1,
    build_synthesis_job_log_v1,
    build_synthesis_observability_catalog_v1,
    build_synthesis_runtime_health_v1,
    evaluate_synthesis_alerts_v1,
    policy_pack_observability_thresholds_v1,
    record_synthesis_job_observability_v1,
    reset_synthesis_observability_metrics_v1,
    snapshot_synthesis_metrics_v1,
    verify_gp08_obs01_metrics_and_health_static,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-synthesis-runtime-architecture.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_OBSERVABILITY_RUNTIME_SCHEMA_VERSION >= 1


def test_gp08_obs01_static_gate() -> None:
    reset_synthesis_observability_metrics_v1()
    reset_synthesis_omission_histogram_v1()
    out = verify_gp08_obs01_metrics_and_health_static()
    assert out["passed"] is True
    assert out["id"] == GP08_OBS01_GATE_ID_V1


def test_job_log_has_no_claim_payloads() -> None:
    log = build_synthesis_job_log_v1(
        envelope={
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
        },
        job_id="job-1",
        status="completed",
        synthesis_legality_class="synthesis_replay_safe",
        duration_ms=9,
        omission_count=2,
    )
    assert log["omission_count"] == 2
    assert "claims" not in log


def test_metric_increment() -> None:
    reset_synthesis_observability_metrics_v1()
    before = snapshot_synthesis_metrics_v1()["synthesis_jobs_total"]
    record_synthesis_job_observability_v1(
        tenant_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        envelope={
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
        },
        status="completed",
        synthesis_legality_class="synthesis_replay_safe",
        duration_ms=100,
        llm_invocations=[{"model_route_id": "struct-v1", "tokens_used": 42}],
    )
    after = snapshot_synthesis_metrics_v1()
    assert after["synthesis_jobs_total"] == before + 1
    assert after["synthesis_llm_tokens_by_route"].get("struct-v1", 0) >= 42


def test_policy_pack_observability_thresholds() -> None:
    th = policy_pack_observability_thresholds_v1()
    assert th["completeness_critical_percent"] == 50
    assert th["job_failure_rate_percent"] == 10


def test_alert_evaluation_critical_sd() -> None:
    alerts = evaluate_synthesis_alerts_v1(
        health={
            "synthesis_completeness_percent": 10,
            "publication_lag_epochs": 2,
            "sd_critical_count": 1,
            "substrate_health_state": "critical",
            "recent_critical_sd_artifacts_1h": 5,
            "tenant_job_failure_percent": 20,
        },
        metrics={"synthesis_replay_divergence_total": 0},
        thresholds=policy_pack_observability_thresholds_v1(),
        tenant_jobs_present=2,
    )
    ids = {a["alert_id"] for a in alerts}
    assert "synthesis_coverage_critical" in ids
    assert "sd_critical_spike" in ids


def test_observability_catalog() -> None:
    cat = build_synthesis_observability_catalog_v1()
    assert cat["gate_id"] == GP08_OBS01_GATE_ID_V1
    assert "synthesis_jobs_total" in cat["metric_names"]


def test_doctrine_files_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "synthesis" / "phase-08-synthesis-runtime-architecture.md").read_text(
        encoding="utf-8",
    )
    assert "synthesis_jobs_total" in text


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8obs-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Obs")
    tenant = Tenant(
        company_name="P8OBS",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8obs-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_runtime_health_and_job_observability(db_session: Session) -> None:
    reset_synthesis_observability_metrics_v1()
    tenant_id = _tenant(db_session)
    body = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
        "pinned_retrieval_receipt": {
            "retrieval_response": {
                "retrieval_legality_class": "retrieval_replay_safe",
                PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-obs21",
                "retrieval_evidence_hits": [],
                "retrieval_omission_rows": [],
                "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
                "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
            },
        },
    }
    before = snapshot_synthesis_metrics_v1()["synthesis_jobs_total"]
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    db_session.commit()
    assert isinstance(out.get("synthesis_job_log"), dict)
    after = snapshot_synthesis_metrics_v1()["synthesis_jobs_total"]
    assert after >= before + 1
    health = build_synthesis_runtime_health_v1(db_session, tenant_id=tenant_id)
    assert health.get("substrate_state") is not None
    assert "s_leg_health" in health
    strip = build_synthesis_health_strip_v1(db_session, tenant_id=tenant_id)
    assert "active_alerts" in strip
