"""P04-05 — candidate regen hash, authoritative replay hash, promotion policy, Celery hooks."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.celery_app import celery_app
from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.authoritative_writer import (
    PromotionInvariantError,
    create_promotion_policy,
    promote_candidate_to_authoritative_link,
)
from vector.domains.cortex.identity.candidate_generation import (
    compute_candidate_set_sha256,
    regenerate_link_candidates,
    verify_authoritative_replay_hash_static,
    verify_candidate_regen_hash_static,
)
from vector.domains.cortex.identity.link_ledger import (
    LinkLedgerInvariantError,
    append_authoritative_org_link,
    compute_authoritative_link_set_sha256,
)
from vector.domains.cortex.identity.org_entities import upsert_org_entity


def test_celery_registers_link_identity_tasks() -> None:
    assert "vector.cortex.identity.regenerate_link_candidates" in celery_app.tasks
    assert "vector.cortex.identity.replay_authoritative_links" in celery_app.tasks


def test_verify_gp04_04_and_gp04_05_static_gates() -> None:
    g4 = verify_candidate_regen_hash_static()
    assert g4["id"] == "G-P04-04"
    assert g4["passed"] is True
    g5 = verify_authoritative_replay_hash_static()
    assert g5["id"] == "G-P04-05"
    assert g5["passed"] is True


def test_compute_candidate_set_sha256_stable_under_permutation() -> None:
    base = [
        {"link_type": "a", "source_entity_id": "s", "target_entity_id": "t", "evidence_raw_record_ids": [2, 1], "rule_id": None},
        {"link_type": "b", "source_entity_id": "s", "target_entity_id": "u", "evidence_raw_record_ids": [], "rule_id": "r"},
    ]
    assert compute_candidate_set_sha256(base) == compute_candidate_set_sha256(list(reversed(base)))


def test_append_rejects_partial_promotion_fields() -> None:
    tid = uuid.uuid4()
    sid = uuid.uuid4()
    tid2 = uuid.uuid4()
    with pytest.raises(LinkLedgerInvariantError):
        append_authoritative_org_link(
            None,  # type: ignore[arg-type]
            tenant_id=tid,
            link_type="org.persona_belongs_to_handle",
            source_entity_id=sid,
            target_entity_id=tid2,
            evidence_raw_record_ids=[1],
            promoted_from_candidate_id=uuid.uuid4(),
            promotion_policy_id=None,
        )


@pytest.mark.integration
def test_regenerate_promote_and_replay_hash(
    db_session: Session,
) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p405-{uuid.uuid4().hex[:8]}@example.com", full_name="P405")
    tenant = Tenant(
        company_name="P405 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p405-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    e1 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "a"},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "b"},
        metadata_json={},
    )
    db_session.commit()

    out = regenerate_link_candidates(
        db_session,
        tenant_id=tenant.id,
        rule_version="p04.step05.test.v1",
        rows=[
            {
                "link_type": "org.persona_belongs_to_handle",
                "source_entity_id": str(e1.id),
                "target_entity_id": str(e2.id),
                "evidence_raw_record_ids": [9001],
                "rule_id": None,
            }
        ],
    )
    assert out["candidate_set_sha256"]
    bid = uuid.UUID(out["candidate_batch_id"])
    from vector.domains.cortex.identity.candidate_generation import list_candidates_for_batch

    cands = list_candidates_for_batch(db_session, tenant_id=tenant.id, batch_id=bid)
    assert len(cands) == 1

    pol = create_promotion_policy(db_session, tenant_id=tenant.id, policy_ref="policy.p04.step05.promote.v1")
    link = promote_candidate_to_authoritative_link(
        db_session,
        tenant_id=tenant.id,
        candidate_id=cands[0].id,
        promotion_policy_id=pol.id,
    )
    db_session.commit()
    assert link.promoted_from_candidate_id == cands[0].id
    assert link.promotion_policy_id == pol.id

    h1 = compute_authoritative_link_set_sha256(db_session, tenant_id=tenant.id)
    h2 = compute_authoritative_link_set_sha256(db_session, tenant_id=tenant.id)
    assert h1 == h2


@pytest.mark.integration
def test_promotion_requires_policy_id(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p405b-{uuid.uuid4().hex[:8]}@example.com", full_name="P405b")
    tenant = Tenant(
        company_name="P405b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p405b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    e1 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "x"},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "y"},
        metadata_json={},
    )
    reg = regenerate_link_candidates(
        db_session,
        tenant_id=tenant.id,
        rule_version="p04.step05.policyfail",
        rows=[
            {
                "link_type": "org.persona_belongs_to_handle",
                "source_entity_id": str(e1.id),
                "target_entity_id": str(e2.id),
                "evidence_raw_record_ids": [1],
                "rule_id": None,
            }
        ],
    )
    cid = uuid.UUID(reg["candidate_batch_id"])
    from vector.domains.cortex.identity.candidate_generation import list_candidates_for_batch

    c = list_candidates_for_batch(db_session, tenant_id=tenant.id, batch_id=cid)[0]
    wrong_pol = uuid.uuid4()
    with pytest.raises(PromotionInvariantError):
        promote_candidate_to_authoritative_link(
            db_session,
            tenant_id=tenant.id,
            candidate_id=c.id,
            promotion_policy_id=wrong_pol,
        )


@pytest.mark.integration
def test_canonical_verification_includes_gp04_cand_gates(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p405c-{uuid.uuid4().hex[:8]}@example.com", full_name="P405c")
    tenant = Tenant(
        company_name="P405c Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p405c-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    ids = [g["id"] for g in out["gates"]]
    for gid in ("G-P04-04", "G-P04-05", "G-P04-CAND-01"):
        assert gid in ids
        assert next(g for g in out["gates"] if g["id"] == gid)["passed"] is True


@pytest.mark.integration
def test_admin_link_candidate_queue(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p405d-{uuid.uuid4().hex[:8]}@example.com", full_name="P405d")
    tenant = Tenant(
        company_name="P405d Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p405d-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    e1 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "m"},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "n"},
        metadata_json={},
    )
    regenerate_link_candidates(
        db_session,
        tenant_id=tenant.id,
        rule_version="p04.admin.queue",
        rows=[
            {
                "link_type": "org.persona_belongs_to_handle",
                "source_entity_id": str(e1.id),
                "target_entity_id": str(e2.id),
                "evidence_raw_record_ids": [77],
                "rule_id": None,
            }
        ],
    )
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/link-candidates",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["batches"]
    assert body["batches"][0]["candidates"]
