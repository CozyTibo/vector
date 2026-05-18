"""Phase 08 Step 19 — substrate completeness projection (synthesis stage)."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness.substrate_completeness_ledger import (
    build_substrate_completeness_ledger_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    GP08_COMP01_GATE_ID_V1,
    PHASE08_SYNTHESIS_COMPLETENESS_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_STAGE_OMISSION_NEVER_SYNTHESIZED_V1,
    SynthesisCompletenessError,
    assert_synthesis_never_idle_healthy_when_eligible_v1,
    compute_synthesis_lag_epochs_v1,
    derive_synthesis_stage_substrate_state_v1,
    pipeline_default_workloads_v1,
    project_synthesis_completeness_v1,
    verify_gp08_comp01_coverage_threshold_static,
    verify_gp08_comp01_never_idle_healthy_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-synthesis-runtime-architecture.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_COMPLETENESS_RUNTIME_SCHEMA_VERSION >= 1


def test_static_comp_gates() -> None:
    assert verify_gp08_comp01_never_idle_healthy_static()["passed"] is True
    assert verify_gp08_comp01_never_idle_healthy_static()["id"] == GP08_COMP01_GATE_ID_V1
    assert verify_gp08_comp01_coverage_threshold_static()["passed"] is True


def test_pipeline_default_workloads_from_fixture() -> None:
    workloads = pipeline_default_workloads_v1()
    assert "execution_understanding" in workloads
    assert "degradation_brief" in workloads


def test_never_idle_healthy_law() -> None:
    with pytest.raises(SynthesisCompletenessError, match="synthesis_idle_healthy"):
        assert_synthesis_never_idle_healthy_when_eligible_v1(
            eligible_scopes=6,
            synthesized_scopes=0,
            substrate_state="healthy",
        )


def test_lag_epochs_behind_index() -> None:
    lag = compute_synthesis_lag_epochs_v1(
        published_index_epoch="epoch-a",
        synthesis_publication_epoch="epoch-b",
    )
    assert lag["publication_behind_index"] is True
    assert lag["lag_epochs"] == 1


def test_derive_state_never_synthesized_degraded() -> None:
    state = derive_synthesis_stage_substrate_state_v1(
        eligible_scopes=4,
        synthesized_scopes=0,
        coverage_percent=0.0,
        substrate_health_state="unresolved",
        publication_behind_index=True,
    )
    assert state == "degraded"


def test_ledger_includes_synthesis_stage(monkeypatch: pytest.MonkeyPatch) -> None:
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

    for sid, label, route in (
        ("ingestion", "Raw", "/i"),
        ("canonical", "C", "/c"),
        ("identity", "I", "/id"),
        ("graph", "G", "/g"),
        ("traversal", "T", "/t"),
        ("tcre", "R", "/r"),
        ("retrieval", "Retrieval", "/ret"),
    ):
        monkeypatch.setitem(
            ledger_mod._STAGE_PROJECTORS_V1,
            sid,
            lambda *a, sid=sid, label=label, route=route, **k: _stage(sid, label, route),
        )
    monkeypatch.setitem(
        ledger_mod._STAGE_PROJECTORS_V1,
        "synthesis",
        lambda *a, **k: _stage(
            "synthesis",
            "Synthesis",
            "/syn",
            substrate_state="degraded",
            omission_classes={SYNTHESIS_STAGE_OMISSION_NEVER_SYNTHESIZED_V1: 1},
            metrics={"eligible_scopes": 4, "synthesized_scopes": 0},
        ),
    )
    out = build_substrate_completeness_ledger_v1(session, tenant_id=uuid.uuid4())
    synthesis_stages = [s for s in out["pipeline_stages"] if s["stage_id"] == "synthesis"]
    assert len(synthesis_stages) == 1
    assert out["aggregate"]["synthesis"]["eligible_scopes"] == 4


def test_doctrine_files_present() -> None:
    root = _repo_root()
    assert (root / "DOCS" / "cortex" / "synthesis" / "phase-08-synthesis-runtime-architecture.md").is_file()


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8comp-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Comp")
    tenant = Tenant(
        company_name="P8COMP",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8comp-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_project_synthesis_completeness_idle_tenant(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    db_session.commit()
    stage = project_synthesis_completeness_v1(db_session, tenant_id=tenant_id)
    assert stage["stage_id"] == "synthesis"
    assert stage["substrate_state"] in ("healthy", "degraded", "critical")
