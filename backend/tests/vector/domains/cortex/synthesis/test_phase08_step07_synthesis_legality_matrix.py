"""P08-07 — Synthesis legality matrix (``synthesis.synthesis_legality_matrix``)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.phase_boundaries import SD_REPLAY_TWIN_V1
from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
    GP08_LEG01_GATE_ID_V1,
    PHASE08_SYNTHESIS_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_LEGALITY_CLASS_ORDINALS_V1,
    SYNTHESIS_LEGALITY_CLASSES_V1,
    SynthesisLegalityError,
    aggregate_synthesis_legality_class_v1,
    assert_synthesis_job_lawful_v1,
    build_synthesis_legality_matrix_catalog_v1,
    build_synthesis_legality_posture_v1,
    cap_exploration_partition_legality_v1,
    max_synthesis_legality_class_v1,
    verify_gp08_leg01_synthesis_legality_matrix_static,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8leg-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Leg User")
    tenant = Tenant(
        company_name="P8LEG",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8leg-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_phase08_synthesis_legality_matrix_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION >= 1


def test_five_synthesis_legality_classes_with_ordinals() -> None:
    assert len(SYNTHESIS_LEGALITY_CLASSES_V1) == 5
    assert SYNTHESIS_LEGALITY_CLASS_ORDINALS_V1["synthesis_forbidden"] == 4


def test_max_synthesis_legality_picks_worst() -> None:
    assert max_synthesis_legality_class_v1(
        "synthesis_replay_safe",
        "synthesis_degraded",
    ) == "synthesis_degraded"


def test_s_leg02_replay_twin_yields_degraded() -> None:
    agg = aggregate_synthesis_legality_class_v1(
        upstream_retrieval_legality="retrieval_replay_safe",
        synthesis_intent="inspect",
        execution_partition="authoritative",
        synthesis_omission_rows=[{"sd_code": SD_REPLAY_TWIN_V1}],
    )
    assert agg == "synthesis_degraded"


def test_upstream_forbidden_yields_synthesis_forbidden() -> None:
    agg = aggregate_synthesis_legality_class_v1(
        upstream_retrieval_legality="retrieval_forbidden",
        synthesis_intent="inspect",
        execution_partition="authoritative",
    )
    assert agg == "synthesis_forbidden"


def test_exploration_partition_caps_at_partial() -> None:
    capped = cap_exploration_partition_legality_v1("synthesis_unverifiable")
    assert capped == "synthesis_partial"


def test_fail_closed_unverifiable_inspect() -> None:
    with pytest.raises(SynthesisLegalityError, match="synthesis_fail_closed"):
        assert_synthesis_job_lawful_v1(
            legality_class="synthesis_unverifiable",
            synthesis_intent="inspect",
        )


def test_audit_allows_unverifiable() -> None:
    assert_synthesis_job_lawful_v1(
        legality_class="synthesis_unverifiable",
        synthesis_intent="audit",
    )


def test_verify_gp08_leg01_static_passes() -> None:
    out = verify_gp08_leg01_synthesis_legality_matrix_static()
    assert out["id"] == GP08_LEG01_GATE_ID_V1
    assert out["passed"] is True


def test_legality_matrix_catalog_has_seven_predicates() -> None:
    cat = build_synthesis_legality_matrix_catalog_v1()
    assert cat["surface_kind"] == "doctrine_catalog"
    assert len(cat["predicates"]) == 7


def test_orchestrator_classify_sets_legality_on_job(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    out = execute_synthesis_job_envelope_v1(
        db_session,
        tenant_id=tenant_id,
        body={
            "schema_version": 1,
            "tenant_id": str(tenant_id),
            "synthesis_workload_class": "pipeline_default",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
        },
    )
    assert out["synthesis_legality_class"] in SYNTHESIS_LEGALITY_CLASSES_V1
    posture = build_synthesis_legality_posture_v1(
        legality_class=out["synthesis_legality_class"],
        synthesis_intent="inspect",
        execution_partition="authoritative",
        s_leg=out["synthesis_legality_posture"].get("s_leg_snapshot", {}),
        upstream_retrieval_legality="retrieval_replay_safe",
    )
    assert posture["synthesis_legality_class"] == out["synthesis_legality_class"]
