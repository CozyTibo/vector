"""P085-23 — Retrieval completeness propagation (**G-P085-RET-PROP-01**)."""

from __future__ import annotations

import uuid
from typing import Any
import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness.completeness_degradation_projection import (
    build_degradation_propagation_chain_v1,
)
from vector.domains.cortex.completeness.substrate_completeness_ledger import (
    build_substrate_completeness_ledger_v1,
)
from vector.domains.cortex.operational_runtime.cesp_retrieval_propagation_gate import (
    verify_gp085_retrieval_propagation_gate_static,
)
from vector.domains.cortex.operational_runtime.fake_green_prohibition import (
    OPERATIONAL_IDLE_HEALTHY_IDLE_V1,
    OPERATIONAL_IDLE_STARVATION_V1,
)
from vector.domains.cortex.operational_runtime.retrieval_completeness_propagation import (
    GP085_RET_PROP01_GATE_ID_V1,
    RETRIEVAL_CARD_CLASSIFICATION_HEALTHY_IDLE_V1,
    RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1,
    RETRIEVAL_STAGE_OMISSION_OPERATIONAL_STARVATION_V1,
    build_retrieval_completeness_propagation_catalog_v1,
    classify_retrieval_card_v1,
    derive_retrieval_completeness_substrate_state_v1,
    evaluate_retrieval_card_fake_green_v1,
    propagate_retrieval_completeness_stage_v1,
    verify_gp085_ret_prop01_static,
)
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    project_retrieval_completeness_v1,
)


def test_propagation_catalog() -> None:
    cat = build_retrieval_completeness_propagation_catalog_v1()
    assert cat["primary_gate_id"] == GP085_RET_PROP01_GATE_ID_V1
    assert cat["p0_gap_closed"] == "P0-085-04"
    assert RETRIEVAL_STAGE_OMISSION_OPERATIONAL_STARVATION_V1 in cat["retrieval_stage_omission_classes"]


def test_verify_gp085_ret_prop01_static_passes() -> None:
    assert verify_gp085_ret_prop01_static()["passed"] is True
    assert verify_gp085_retrieval_propagation_gate_static()["passed"] is True


def test_classify_card_starved_vs_idle() -> None:
    assert (
        classify_retrieval_card_v1(
            eligible=10,
            indexed=0,
            operational_starvation=True,
            idle_class=OPERATIONAL_IDLE_STARVATION_V1,
            upstream_tcre_pending=False,
            upstream_work_present=False,
        )
        == RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1
    )
    assert (
        classify_retrieval_card_v1(
            eligible=0,
            indexed=0,
            operational_starvation=False,
            idle_class=OPERATIONAL_IDLE_HEALTHY_IDLE_V1,
            upstream_tcre_pending=False,
            upstream_work_present=False,
        )
        == RETRIEVAL_CARD_CLASSIFICATION_HEALTHY_IDLE_V1
    )


def test_p0_085_04_upstream_tcre_pending_degrades() -> None:
    assert (
        derive_retrieval_completeness_substrate_state_v1(
            eligible=0,
            indexed=0,
            coverage_percent=0.0,
            published_epoch=None,
            replay_posture="unknown",
            pending_index_builds=0,
            upstream_tcre_pending=True,
            upstream_work_present=True,
            operational_starvation=False,
            index_stale=False,
            fake_green_blocked=False,
        )
        == "degraded"
    )


def test_fake_green_eligible_unindexed() -> None:
    fg = evaluate_retrieval_card_fake_green_v1(
        eligible=3,
        indexed=0,
        substrate_state="healthy",
        operational_starvation=False,
        upstream_tcre_pending=False,
    )
    assert fg["fake_green_blocked"] is True


def test_degradation_chain_operational_starvation_to_synthesis() -> None:
    stages = [
        {
            "stage_id": "retrieval",
            "omission_classes": {RETRIEVAL_STAGE_OMISSION_OPERATIONAL_STARVATION_V1: 1},
        },
        {"stage_id": "synthesis", "omission_classes": {}},
    ]
    chain = build_degradation_propagation_chain_v1(stages)
    assert any(
        e["propagation_consequence"] == "synthesis_starved_from_retrieval_operational_starvation"
        for e in chain
    )


def test_project_retrieval_delegates_to_propagation(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tid = uuid.uuid4()
    expected = {
        "stage_id": "retrieval",
        "total_objects": 5,
        "processed_count": 2,
        "metrics": {"retrieval_completeness_propagation": {"gate_id": GP085_RET_PROP01_GATE_ID_V1}},
    }
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.retrieval_completeness_propagation.propagate_retrieval_completeness_stage_v1",
        lambda *_a, **_k: expected,
    )
    out = project_retrieval_completeness_v1(db_session, tenant_id=tid)
    assert out == expected


@pytest.mark.integration
def test_propagate_retrieval_card_laws_empty_tenant(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085retprop-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Ret Prop",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    stage = propagate_retrieval_completeness_stage_v1(db_session, tenant_id=row.id)
    assert stage["stage_id"] == "retrieval"
    assert stage["total_objects"] == stage["metrics"]["eligible_artifact_count"]
    assert stage["processed_count"] == stage["metrics"]["indexed_count"]
    prop = stage["metrics"]["retrieval_completeness_propagation"]
    assert prop["gate_id"] == GP085_RET_PROP01_GATE_ID_V1
    assert prop["retrieval_card_classification"] == RETRIEVAL_CARD_CLASSIFICATION_HEALTHY_IDLE_V1


def test_ledger_retrieval_stage_uses_propagation(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085retled-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 Ret Led",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    def _fake_project(session: Session, *, tenant_id: uuid.UUID, stage_id: str) -> dict[str, Any]:
        base = {
            "substrate_state": "healthy",
            "total_objects": 0,
            "processed_count": 0,
            "degraded_count": 0,
            "unresolved_count": 0,
            "omitted_count": 0,
            "degraded_percent": 0.0,
            "unresolved_percent": 0.0,
            "drift_warnings": [],
            "omission_classes": {},
            "metrics": {},
        }
        if stage_id == "retrieval":
            return {
                **base,
                "stage_id": "retrieval",
                "substrate_state": "degraded",
                "total_objects": 8,
                "unresolved_count": 8,
                "unresolved_percent": 100.0,
                "omission_classes": {RETRIEVAL_STAGE_OMISSION_OPERATIONAL_STARVATION_V1: 1},
                "metrics": {
                    "retrieval_coverage_percent": 0.0,
                    "replay_safe_query_percent": 0.0,
                    "retrieval_never_indexed": True,
                    "walk_record_count": 0,
                    "retrieval_card_classification": RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1,
                    "retrieval_completeness_propagation": {"gate_id": GP085_RET_PROP01_GATE_ID_V1},
                },
            }
        return {**base, "stage_id": stage_id}

    monkeypatch.setattr(
        "vector.domains.cortex.completeness.substrate_completeness_ledger._project_stage_safe_v1",
        _fake_project,
    )
    ledger = build_substrate_completeness_ledger_v1(db_session, tenant_id=tenant.id)
    retrieval = next(s for s in ledger["pipeline_stages"] if s["stage_id"] == "retrieval")
    assert retrieval["metrics"]["retrieval_card_classification"] == RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1
