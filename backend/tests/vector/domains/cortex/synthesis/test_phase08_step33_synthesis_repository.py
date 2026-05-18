"""Phase 08 Step 33 — synthesis durable store repository."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.synthesis.synthesis_repository import (
    SynthesisRepositoryError,
    apply_synthesis_retention_policy_v1,
    assert_synthesis_idempotency_key_v1,
    build_synthesis_durable_store_catalog_v1,
    create_synthesis_job_row_v1,
    find_idempotent_synthesis_job_v1,
    run_synthesis_durable_store_load_smoke_v1,
    verify_gp08_store01_synthesis_durable_store_static,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def test_durable_store_catalog() -> None:
    catalog = build_synthesis_durable_store_catalog_v1()
    assert "uq_cortex_synthesis_jobs_tenant_idem_digest_completed" in catalog["indexes"]
    assert catalog["retention_policy"]["never_delete_published_artifacts"] is True


def test_static_store_gate() -> None:
    assert verify_gp08_store01_synthesis_durable_store_static()["passed"] is True


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8store-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Store")
    tenant = Tenant(
        company_name="P8STORE",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8store-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_idempotency_find_and_conflict(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    idem = f"idem-{uuid.uuid4().hex[:8]}"
    digest_a = hash_reasoning_canonical_json_sha256_v1({"v": "a"})
    digest_b = hash_reasoning_canonical_json_sha256_v1({"v": "b"})
    envelope = {
        "schema_version": 1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "idempotency_key": idem,
    }
    job = create_synthesis_job_row_v1(
        db_session,
        tenant_id=tenant_id,
        envelope=envelope,
        envelope_digest=digest_a,
    )
    job.status = "completed"
    job.receipt_digest = digest_a
    db_session.flush()

    found = find_idempotent_synthesis_job_v1(
        db_session,
        tenant_id=tenant_id,
        idempotency_key=idem,
        envelope_digest=digest_a,
    )
    assert found is not None
    assert found.id == job.id

    with pytest.raises(SynthesisRepositoryError, match="idempotency_key_digest_mismatch"):
        assert_synthesis_idempotency_key_v1(
            db_session,
            tenant_id=tenant_id,
            idempotency_key=idem,
            envelope_digest=digest_b,
        )


@pytest.mark.integration
def test_retention_dry_run(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    out = apply_synthesis_retention_policy_v1(db_session, tenant_id=tenant_id, dry_run=True)
    assert out["dry_run"] is True
    assert out["deletes_executed"] is False


@pytest.mark.integration
def test_load_smoke(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    out = run_synthesis_durable_store_load_smoke_v1(db_session, tenant_id=tenant_id, iterations=4)
    assert out["passed"] is True
    assert out["idempotency_hit"] is True
