"""Wave 8 — operational simplicity pass."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.scheduling import verify_wave8_operational_simplicity_v1
from vector.domains.cortex.identity.failure_remediation import validate_org_remediation
from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
    discover_repo_root_v1,
    verify_substrate_coherence_ci_gates_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_operational_simplicity_v1 import (
    SUBSTRATE_MUTATORS_V1,
    is_substrate_replay_job_kind_collapsed_v1,
    predict_next_mutation_hint_v1,
    verify_wave8_operational_simplicity_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_truth_v1 import build_substrate_truth_v1
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"w8-{uuid.uuid4().hex[:10]}@example.com", full_name="W8")
    tenant = Tenant(
        company_name="W8 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"w8-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_mutator_registry_has_nine_entries() -> None:
    assert len(SUBSTRATE_MUTATORS_V1) == 9


def test_predict_next_mutation_hint_dirty() -> None:
    hint = predict_next_mutation_hint_v1(
        lease_status="DIRTY",
        phase_cursor="03_identity",
        is_dirty=True,
        topology_wait=False,
        may_proceed_despite_topology=False,
    )
    assert "dual-lane" in hint


def test_substrate_replay_job_kinds_collapsed() -> None:
    assert is_substrate_replay_job_kind_collapsed_v1("identity_continuity_rebuild") is True
    assert is_substrate_replay_job_kind_collapsed_v1("candidate_regen") is False


def test_verify_wave8_operational_simplicity_v1() -> None:
    root = discover_repo_root_v1()
    errors = verify_wave8_operational_simplicity_v1(repo_root=root)
    assert errors == []


def test_verify_wave8_scheduling_wrapper() -> None:
    assert verify_wave8_operational_simplicity_v1() == []


def test_build_substrate_truth_includes_operational_panel(db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    truth = build_substrate_truth_v1(db_session, tenant_id=tid, settings=get_settings())
    op = truth.get("operational") or {}
    assert op.get("surface_kind") == "substrate_operational_v1"
    assert "next_mutation_hint" in op
    assert "canonical_topology_gate" in op
    assert "dual_lane" in op


def test_failure_remediation_rejects_substrate_replay_job(db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    out = validate_org_remediation(
        db_session,
        tenant_id=tid,
        remediation_class="org_link_replay_retry",
        dry_run=True,
        confirm_execution=False,
        failure_case_gap_id=None,
        payload={"job_kind": "identity_continuity_rebuild"},
    )
    assert out["validation"]["result_status"] == "failed"
    detail = out["validation"]["result_detail_json"]
    assert detail.get("reason") == "substrate_replay_job_collapsed"


def test_coherence_ci_includes_wave8() -> None:
    assert verify_substrate_coherence_ci_gates_v1() == []
