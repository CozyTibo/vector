"""P07-07 — Query legality matrix + degradation class floors."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_degradation_projection import (
    RETRIEVAL_LEGALITY_CLASS_DEGRADATION_FLOOR_V1,
    apply_retrieval_legality_degradation_floor_v1,
    build_retrieval_degradation_envelope_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_matrix import (
    GP07_LEG01_GATE_ID_V1,
    PHASE07_RETRIEVAL_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_LEGALITY_MATRIX_CONTRACT_V1,
    RETRIEVAL_QUERY_LEGALITY_CLASS_ORDINALS_V1,
    aggregate_query_legality_class_v1,
    build_retrieval_legality_matrix_catalog_v1,
    build_retrieval_legality_posture_v1,
    build_retrieval_queries_by_legality_histogram_v1,
    max_retrieval_legality_class_v1,
    run_retrieval_r_leg_precheck_v1,
    verify_gp07_leg01_retrieval_legality_matrix_static,
)
from vector.domains.cortex.retrieval.retrieval_legality_projection import (
    RetrievalLegalityError,
    assert_retrieval_query_lawful_v1,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)


def _repo_root_containing_phase07_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "retrieval-legality-matrix.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/retrieval/ from test file parents.")


def test_phase07_legality_matrix_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION >= 1


def test_five_legality_classes_with_ordinals() -> None:
    assert len(RETRIEVAL_QUERY_LEGALITY_CLASS_ORDINALS_V1) == 5
    assert RETRIEVAL_QUERY_LEGALITY_CLASS_ORDINALS_V1["retrieval_replay_safe"] == 0
    assert RETRIEVAL_QUERY_LEGALITY_CLASS_ORDINALS_V1["retrieval_forbidden"] == 4


def test_max_legality_picks_worst_class() -> None:
    assert max_retrieval_legality_class_v1(
        "retrieval_replay_safe", "retrieval_degraded"
    ) == "retrieval_degraded"
    assert max_retrieval_legality_class_v1(
        "retrieval_partial", "retrieval_unverifiable"
    ) == "retrieval_unverifiable"


def test_r_leg03_failure_yields_unverifiable_aggregate() -> None:
    agg = aggregate_query_legality_class_v1(
        r_leg={
            "R-LEG-01": True,
            "R-LEG-02": True,
            "R-LEG-03": False,
            "R-LEG-04": True,
            "R-LEG-05": True,
            "R-LEG-06": True,
            "R-LEG-07": True,
        },
        upstream_row_legality="retrieval_replay_safe",
        intent="inspect",
    )
    assert agg == "retrieval_unverifiable"


def test_evidence_unverifiable_floor_unless_audit() -> None:
    agg = aggregate_query_legality_class_v1(
        r_leg={f"R-LEG-{i:02d}": True for i in range(1, 8)},
        upstream_row_legality="retrieval_replay_safe",
        intent="inspect",
        hit_evidence_legalities=["evidence_unverifiable"],
    )
    assert agg == "retrieval_unverifiable"
    audit = aggregate_query_legality_class_v1(
        r_leg={f"R-LEG-{i:02d}": True for i in range(1, 8)},
        upstream_row_legality="retrieval_replay_safe",
        intent="audit",
        hit_evidence_legalities=["evidence_unverifiable"],
    )
    assert audit == "retrieval_replay_safe"


def test_fail_closed_unverifiable_inspect() -> None:
    with pytest.raises(RetrievalLegalityError, match="retrieval_fail_closed"):
        assert_retrieval_query_lawful_v1(
            legality_class="retrieval_unverifiable",
            replay_posture="unsafe",
            intent="inspect",
        )


def test_audit_allows_unverifiable_response() -> None:
    assert_retrieval_query_lawful_v1(
        legality_class="retrieval_unverifiable",
        replay_posture="unsafe",
        intent="audit",
    )


def test_partial_requires_audit_in_authoritative_partition() -> None:
    with pytest.raises(RetrievalLegalityError, match="retrieval_partial_requires_audit"):
        assert_retrieval_query_lawful_v1(
            legality_class="retrieval_partial",
            replay_posture="partial",
            intent="inspect",
            execution_partition="authoritative",
        )


def test_degradation_floor_maps_legality_class() -> None:
    assert RETRIEVAL_LEGALITY_CLASS_DEGRADATION_FLOOR_V1["retrieval_degraded"] == "degraded"
    assert (
        apply_retrieval_legality_degradation_floor_v1(
            degradation_posture="stable",
            retrieval_legality_class="retrieval_degraded",
        )
        == "degraded"
    )


def test_degradation_envelope_includes_legality_floor() -> None:
    env = build_retrieval_degradation_envelope_v1(
        degradation_posture="stable",
        omission_summary={"rd": ["RD-TCRE-GAP"]},
        retrieval_legality_class="retrieval_degraded",
        r_leg_violations=["R-LEG-05"],
    )
    assert env["degradation_posture"] == "degraded"
    assert env["retrieval_legality_class_floor"] == "retrieval_degraded"
    assert env["r_leg_violations"] == ["R-LEG-05"]


def test_matrix_catalog_shape() -> None:
    cat = build_retrieval_legality_matrix_catalog_v1(tenant_id=uuid.UUID(int=0))
    assert cat["retrieval_legality_matrix_contract"] == RETRIEVAL_LEGALITY_MATRIX_CONTRACT_V1
    assert len(cat["predicates"]) == 7
    assert len(cat["forbidden_deployments"]) == 5
    assert len(cat["legality_classes"]) == 5


def test_verify_gp07_leg01_static_passes() -> None:
    out = verify_gp07_leg01_retrieval_legality_matrix_static()
    assert out["id"] == GP07_LEG01_GATE_ID_V1
    assert out["passed"] is True


def test_doctrine_legality_matrix_file() -> None:
    root = _repo_root_containing_phase07_docs()
    text = (root / "DOCS" / "cortex" / "retrieval" / "retrieval-legality-matrix.md").read_text(
        encoding="utf-8"
    )
    assert "R-LEG-01" in text
    assert "retrieval_replay_safe" in text
    assert "Matrix API" in text


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7leg-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Leg User")
    tenant = Tenant(
        company_name="P7LEG",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7leg-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_legality_histogram_from_index(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=f"replay-{uuid.uuid4().hex[:8]}",
        traversal_epoch="epoch-1",
    )
    db_session.commit()
    hist = build_retrieval_queries_by_legality_histogram_v1(db_session, tenant_id=tenant_id)
    assert sum(hist.values()) >= 1
    assert "retrieval_replay_safe" in hist


@pytest.mark.integration
def test_query_response_includes_legality_posture(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=replay,
        traversal_epoch="epoch-published",
    )
    db_session.commit()
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        retrieval_lookup_id=row.retrieval_lookup_id,
        expected_replay_identity=replay,
        envelope_body={
            "replay_pins": {
                "index_epoch": "epoch-published",
                "tcre_policy_bundle_digest": "sha256:policy-stub",
            },
        },
    )
    assert "retrieval_legality_posture" in out
    assert out["retrieval_legality_posture"]["retrieval_legality_class"] == out[
        "retrieval_legality_class"
    ]


def test_r_leg_precheck_has_seven_keys() -> None:
    snap = run_retrieval_r_leg_precheck_v1(
        {
            "workload_class": "causal_chain",
            "intent": "inspect",
            "addressing": {"retrieval_lookup_id": "sha256:00"},
            "replay_pins": {},
            "upstream_triggers": {},
        }
    )
    assert len(snap) == 7
    assert "R-LEG-01" in snap


def test_legality_posture_marks_unverifiable_pins_required() -> None:
    posture = build_retrieval_legality_posture_v1(
        legality_class="retrieval_unverifiable",
        intent="inspect",
        execution_partition="authoritative",
        r_leg={"R-LEG-03": False},
    )
    assert posture["replay_pins_required"] is True
    assert "R-LEG-03" in posture["r_leg_violations"]
