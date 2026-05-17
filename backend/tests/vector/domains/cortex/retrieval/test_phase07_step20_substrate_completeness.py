"""P07-20 — Substrate completeness + overview (``retrieval.retrieval_completeness_projection``)."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness.substrate_completeness_ledger import (
    build_substrate_completeness_ledger_v1,
)
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    GP07_COMP01_GATE_ID_V1,
    PHASE07_RETRIEVAL_COMPLETENESS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_STAGE_OMISSION_INDEX_NEVER_BUILT_V1,
    RetrievalCompletenessError,
    assert_retrieval_never_idle_healthy_when_eligible_v1,
    derive_retrieval_stage_substrate_state_v1,
    project_retrieval_completeness_v1,
    verify_gp07_comp01_coverage_threshold_static,
    verify_gp07_comp01_never_idle_healthy_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-completeness-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_COMPLETENESS_RUNTIME_SCHEMA_VERSION >= 1


def test_static_comp_gates() -> None:
    assert verify_gp07_comp01_never_idle_healthy_static()["passed"] is True
    assert verify_gp07_comp01_never_idle_healthy_static()["id"] == GP07_COMP01_GATE_ID_V1
    assert verify_gp07_comp01_coverage_threshold_static()["passed"] is True


def test_never_idle_healthy_law() -> None:
    with pytest.raises(RetrievalCompletenessError, match="retrieval_idle_healthy"):
        assert_retrieval_never_idle_healthy_when_eligible_v1(
            eligible_artifact_count=3,
            indexed_count=0,
            substrate_state="healthy",
        )


def test_derive_state_never_built_degraded() -> None:
    state = derive_retrieval_stage_substrate_state_v1(
        eligible=5,
        indexed=0,
        coverage_percent=0.0,
        published_epoch=None,
        replay_posture="unknown",
        pending_index_builds=1,
    )
    assert state == "degraded"


def test_ledger_includes_retrieval_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    from vector.domains.cortex.completeness import substrate_completeness_ledger as ledger_mod
    from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1

    session = MagicMock()
    session.scalar.return_value = 0
    session.scalars.return_value.all.return_value = []

    def _stage(sid: str, label: str, route: str, **extra: object) -> dict[str, object]:
        metrics = extra.pop("metrics", None)
        omission_classes = extra.pop("omission_classes", None)
        return build_stage_envelope_v1(
            stage_id=sid,
            label=label,
            total_objects=10,
            processed_count=0,
            detail_route=route,
            metrics=metrics if isinstance(metrics, dict) else None,
            omission_classes=omission_classes if isinstance(omission_classes, dict) else None,
            substrate_state=str(extra.get("substrate_state", "healthy")),
        )

    monkeypatch.setitem(
        ledger_mod._STAGE_PROJECTORS_V1,
        "ingestion",
        lambda *a, **k: _stage("ingestion", "Raw", "/i"),
    )
    monkeypatch.setitem(
        ledger_mod._STAGE_PROJECTORS_V1,
        "canonical",
        lambda *a, **k: _stage("canonical", "C", "/c"),
    )
    monkeypatch.setitem(
        ledger_mod._STAGE_PROJECTORS_V1,
        "identity",
        lambda *a, **k: _stage("identity", "I", "/id"),
    )
    monkeypatch.setitem(
        ledger_mod._STAGE_PROJECTORS_V1,
        "graph",
        lambda *a, **k: _stage("graph", "G", "/g"),
    )
    monkeypatch.setitem(
        ledger_mod._STAGE_PROJECTORS_V1,
        "traversal",
        lambda *a, **k: _stage("traversal", "T", "/t"),
    )
    monkeypatch.setitem(
        ledger_mod._STAGE_PROJECTORS_V1,
        "tcre",
        lambda *a, **k: _stage("tcre", "R", "/r"),
    )
    monkeypatch.setitem(
        ledger_mod._STAGE_PROJECTORS_V1,
        "retrieval",
        lambda *a, **k: _stage(
            "retrieval",
            "Retrieval",
            "/ret",
            substrate_state="degraded",
            omission_classes={RETRIEVAL_STAGE_OMISSION_INDEX_NEVER_BUILT_V1: 1},
            metrics={"eligible_artifact_count": 10, "indexed_count": 0, "retrieval_never_indexed": True},
        ),
    )
    out = build_substrate_completeness_ledger_v1(session, tenant_id=uuid.uuid4())
    retrieval_stages = [s for s in out["pipeline_stages"] if s["stage_id"] == "retrieval"]
    assert len(retrieval_stages) == 1
    assert out["aggregate"]["retrieval"]["never_indexed"] is True


def test_doctrine_files_present() -> None:
    root = _repo_root()
    assert (root / "DOCS" / "cortex" / "retrieval" / "phase-07-substrate-overview-integration.md").is_file()


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7comp-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Comp")
    tenant = Tenant(
        company_name="P7COMP",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7comp-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_project_retrieval_completeness_idle_tenant(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    db_session.commit()
    stage = project_retrieval_completeness_v1(db_session, tenant_id=tenant_id)
    assert stage["stage_id"] == "retrieval"
    assert stage["substrate_state"] in ("healthy", "degraded", "critical")


@pytest.mark.integration
def test_indexed_tenant_coverage(db_session: Session) -> None:
    from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
        build_retrieval_coverage_catalog_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_query_engine import index_tcre_chain_for_retrieval_v1

    tenant_id = _tenant(db_session)
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=f"replay-{uuid.uuid4().hex[:8]}",
        traversal_epoch=epoch,
    )
    db_session.commit()
    cov = build_retrieval_coverage_catalog_v1(db_session, tenant_id=tenant_id)
    assert cov["indexed_count"] >= 1
    assert cov["coverage_percent"] >= 0.0
    assert "eligible_artifact_count" in cov
