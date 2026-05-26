"""Wave 7 — substrate API / contract collapse."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.scheduling import verify_wave7_contract_collapse_v1
from vector.domains.cortex.substrate_pipeline.substrate_contract_v1 import (
    build_graph_substrate_v1,
    build_ingest_handoff_v1,
    build_substrate_slice_receipt_v1,
    discover_substrate_contracts_dir_v1,
    validate_phase_receipt_v1,
    validate_substrate_truth_v1,
    verify_wave7_contract_collapse_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
    discover_repo_root_v1,
    verify_substrate_coherence_ci_gates_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_COMPLETED,
    build_substrate_phase_receipt_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_truth_v1 import build_substrate_truth_v1
from vector.domains.cortex.substrate_pipeline.constants import PHASE_03_IDENTITY
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"w7-{uuid.uuid4().hex[:10]}@example.com", full_name="W7")
    tenant = Tenant(
        company_name="W7 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"w7-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_contract_schema_files_exist() -> None:
    root = discover_substrate_contracts_dir_v1()
    assert (root / "substrate_truth_v1.schema.json").is_file()
    assert (root / "phase_receipt_v1.schema.json").is_file()
    repo = discover_repo_root_v1()
    if repo is not None:
        assert (repo / "backend/contracts/substrate_v1.yaml").is_file()


def test_verify_wave7_contract_collapse_v1() -> None:
    root = discover_repo_root_v1()
    errors = verify_wave7_contract_collapse_v1(repo_root=root)
    if root is None:
        assert all("frontend_missing" not in e for e in errors)
    else:
        assert errors == []


def test_build_ingest_handoff_v1_shape() -> None:
    handoff = build_ingest_handoff_v1(dirty_enqueued=True, obligation_epoch=3, reason="sync")
    assert handoff["surface_kind"] == "ingest_handoff_v1"
    assert handoff["dirty_enqueued"] is True
    assert handoff["obligation_epoch"] == 3


def test_validate_phase_receipt_v1_accepts_envelope() -> None:
    tid = uuid.uuid4()
    prid = uuid.uuid4()
    rec = build_substrate_phase_receipt_v1(
        phase_id=PHASE_03_IDENTITY,
        tenant_id=tid,
        pipeline_run_id=prid,
        outcome=PHASE_OUTCOME_COMPLETED,
        raw_output={"bundle_id": "b1"},
        started_at="2026-05-21T00:00:00+00:00",
        completed_at="2026-05-21T00:00:01+00:00",
    )
    env = rec.to_output_envelope()
    assert validate_phase_receipt_v1(env) == []


def test_substrate_slice_receipt_v1_shape() -> None:
    slice_rec = build_substrate_slice_receipt_v1(
        tenant_id=str(uuid.uuid4()),
        bundle_id="default",
        substrate_trigger="repair",
        repair_slice={"identity_substrate_repair": {"entities_upserted": 1}},
    )
    assert slice_rec["surface_kind"] == "substrate_slice_receipt_v1"


def test_build_substrate_truth_v1_validates_against_schema(db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    truth = build_substrate_truth_v1(db_session, tenant_id=tid, settings=get_settings())
    assert truth["graph_substrate"]["surface_kind"] == "graph_substrate_v1"
    assert truth["ingest_handoff"]["surface_kind"] == "ingest_handoff_v1"
    assert "auth_edge_rows" not in truth["graph_substrate"]
    assert validate_substrate_truth_v1(truth) == []


def test_build_graph_substrate_single_auth_metric(db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    graph = build_graph_substrate_v1(db_session, tenant_id=tid)
    assert graph["primary_metric_key"] == "unique_auth_pairs"
    assert "unique_auth_pairs" in graph
    assert graph.get("diagnostics", {}).get("auth_edge_rows") is not None or graph["unique_auth_pairs"] == 0


def test_coherence_ci_includes_wave7() -> None:
    assert verify_substrate_coherence_ci_gates_v1() == []
