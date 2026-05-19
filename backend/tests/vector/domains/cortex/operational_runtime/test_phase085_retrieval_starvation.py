"""P085-22 — retrieval index freshness + starvation (**G-P085-RET-02**)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_retrieval_starvation_gate import (
    verify_gp085_retrieval_starvation_gate_static,
)
from vector.domains.cortex.operational_runtime.fake_green_prohibition import (
    OPERATIONAL_IDLE_HEALTHY_IDLE_V1,
    OPERATIONAL_IDLE_STARVATION_V1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_starvation import (
    GP085_RET02_GATE_ID_V1,
    METRIC_INDEX_STALE_V1,
    METRIC_OPERATIONAL_STARVATION_V1,
    build_substrate_retrieval_starvation_catalog_v1,
    classify_retrieval_idle_class_v1,
    compute_index_freshness_v1,
    evaluate_retrieval_starvation_v1,
    explain_retrieval_eligibility_v1,
    merge_retrieval_starvation_into_completeness_v1,
    verify_gp085_ret02_static,
)
from vector.infrastructure.db.models.cortex_retrieval_index_epoch import (
    CortexRetrievalIndexEpoch,
)


def test_retrieval_starvation_catalog() -> None:
    cat = build_substrate_retrieval_starvation_catalog_v1()
    assert cat["primary_gate_id"] == GP085_RET02_GATE_ID_V1
    assert cat["index_stale_threshold_seconds"] >= 60


def test_verify_gp085_ret02_static_passes() -> None:
    assert verify_gp085_ret02_static()["passed"] is True
    assert verify_gp085_retrieval_starvation_gate_static()["passed"] is True


def test_classify_operational_starvation_tcre() -> None:
    assert (
        classify_retrieval_idle_class_v1(
            eligible=0,
            indexed=0,
            tcre_completed=1,
            walks_completed=0,
            upstream_work_present=True,
        )
        == OPERATIONAL_IDLE_STARVATION_V1
    )


def test_classify_healthy_idle() -> None:
    assert (
        classify_retrieval_idle_class_v1(
            eligible=0,
            indexed=0,
            tcre_completed=0,
            walks_completed=0,
            upstream_work_present=False,
        )
        == OPERATIONAL_IDLE_HEALTHY_IDLE_V1
    )


def test_merge_starvation_into_completeness() -> None:
    omissions, metrics, state = merge_retrieval_starvation_into_completeness_v1(
        omission_classes={},
        metrics={},
        substrate_state="healthy",
        starvation_eval={
            "operational_starvation": True,
            "idle_class": OPERATIONAL_IDLE_STARVATION_V1,
            "index_freshness": {"entry_count": 0, "published_index_epoch": "e1"},
        },
    )
    assert state == "degraded"
    assert metrics[METRIC_OPERATIONAL_STARVATION_V1] is True
    assert "retrieval_index_empty" in omissions


@pytest.mark.integration
def test_index_freshness_stale(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085retst-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 Ret Stale",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    db_session.add(
        CortexRetrievalIndexEpoch(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            index_epoch="epoch-stale",
            build_state="PUBLISHED",
            entry_count=5,
            published_at=datetime.now(tz=UTC) - timedelta(hours=48),
        )
    )
    db_session.flush()

    freshness = compute_index_freshness_v1(db_session, tenant_id=tenant.id)
    assert freshness[METRIC_INDEX_STALE_V1] is True


@pytest.mark.integration
def test_build_retrieval_starvation_panel_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.domains.cortex.operational_runtime.substrate_retrieval_starvation import (
        build_retrieval_starvation_panel_v1,
    )

    slug = f"p085retpan-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Ret Pan",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    panel = build_retrieval_starvation_panel_v1(db_session, tenant_id=row.id)
    assert panel["gate_id"] == GP085_RET02_GATE_ID_V1
    assert panel["idle_class"] == OPERATIONAL_IDLE_HEALTHY_IDLE_V1

    explain = explain_retrieval_eligibility_v1(db_session, tenant_id=row.id)
    assert explain["gate_id"] == GP085_RET02_GATE_ID_V1
    assert explain["operational_starvation"] is False


def test_evaluate_starvation_monkeypatched(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_retrieval_starvation.compute_retrieval_density_metrics_v1",
        lambda *_a, **_k: {
            "substrate_state": "degraded",
            "metrics": {
                "retrieval_eligible_artifact_count": 10,
                "retrieval_indexed_count": 0,
            },
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_retrieval_starvation.count_tcre_completed_jobs_v1",
        lambda *_a, **_k: 2,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_retrieval_starvation.count_completed_walks_v1",
        lambda *_a, **_k: 0,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_retrieval_starvation._upstream_work_present_v1",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_retrieval_starvation.compute_index_freshness_v1",
        lambda *_a, **_k: {
            "index_age_seconds": None,
            "index_stale": False,
            "entry_count": 0,
            "published_index_epoch": None,
        },
    )

    out = evaluate_retrieval_starvation_v1(db_session, tenant_id=tid)
    assert out["operational_starvation"] is True
    assert out["idle_class"] == OPERATIONAL_IDLE_STARVATION_V1
