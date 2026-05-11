"""P04-02 — topology vs org-meaning boundary (boundary_checks)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.canonical.ontology import CanonicalStructuralEdgeKind
from vector.domains.cortex.continuity.edge_contracts import ContinuityEdgeKind
from vector.domains.cortex.identity.boundary_checks import (
    BOUNDARY_CHECKS_VERSION,
    TopologyMeaningBoundaryError,
    validate_org_meaning_link_payload,
    verify_topology_meaning_boundary_static,
)


def test_boundary_checks_version() -> None:
    assert BOUNDARY_CHECKS_VERSION >= 1


def test_rejects_structural_edge_as_link_type() -> None:
    with pytest.raises(TopologyMeaningBoundaryError):
        validate_org_meaning_link_payload(
            {"link_type": CanonicalStructuralEdgeKind.MEMBERSHIP.value}
        )


def test_rejects_continuity_edge_as_org_link_type() -> None:
    with pytest.raises(TopologyMeaningBoundaryError):
        validate_org_meaning_link_payload(
            {"org_link_type": ContinuityEdgeKind.REVIEW_BY_ACTOR.value}
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"structural_edge_kind": "membership"},
        {"canonical_structural_edge_kind": "contained_in"},
        {"materialization_dag_edge": {"from": 1, "to": 2}},
        {"replay_dependency_edge": {"x": 1}},
        {"continuity_edge_contract_version": 1, "edge_kind": "pr_links_issue"},
    ],
)
def test_rejects_forbidden_topology_shapes(payload: dict) -> None:
    with pytest.raises(TopologyMeaningBoundaryError):
        validate_org_meaning_link_payload(payload)


def test_rejects_topology_inside_endpoint() -> None:
    with pytest.raises(TopologyMeaningBoundaryError):
        validate_org_meaning_link_payload(
            {
                "link_type": "org.handle_links_canonical",
                "source": {"structural_edge_kind": "contained_in"},
            }
        )


def test_accepts_minimal_org_meaning_stub() -> None:
    validate_org_meaning_link_payload(
        {
            "link_type": "org.persona_belongs_to_handle",
            "evidence_raw_record_ids": [1, 2, 3],
        }
    )


def test_verify_topology_meaning_boundary_static_passes() -> None:
    gate = verify_topology_meaning_boundary_static()
    assert gate["id"] == "G-P04-08"
    assert gate["passed"] is True


@pytest.mark.integration
def test_canonical_verification_includes_gp04_08_gate(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p402-{uuid.uuid4().hex[:8]}@example.com", full_name="P402")
    tenant = Tenant(
        company_name="P402 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p402-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    ids = [g["id"] for g in out["gates"]]
    assert "G-P04-08" in ids
    gp04 = next(g for g in out["gates"] if g["id"] == "G-P04-08")
    assert gp04["passed"] is True
