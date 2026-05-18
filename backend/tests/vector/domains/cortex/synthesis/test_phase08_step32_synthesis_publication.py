"""Phase 08 Step 32 — synthesis publication barrier (**G-P08-REPLAY-02**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_bounded_caps import SD_PUBLISH_BLOCKED_V1
from vector.domains.cortex.synthesis.synthesis_publication import (
    SynthesisPublicationError,
    assert_publication_epoch_monotonic_v1,
    build_synthesis_publication_law_catalog_v1,
    build_synthesis_publication_status_v1,
    compare_gp08_replay02_publication_monotonicity_v1,
    evaluate_artifact_publish_eligibility_v1,
    parse_synthesis_publication_epoch_seq_v1,
    publish_synthesis_epoch_v1,
    retract_synthesis_artifact_v1,
    verify_gp08_pub01_publication_barrier_module_static,
)
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    verify_gp08_replay02_publication_epoch_forward_only_static,
)
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def test_publication_law_catalog() -> None:
    law = build_synthesis_publication_law_catalog_v1()
    assert law["forward_only"] is True
    assert SD_PUBLISH_BLOCKED_V1 == law["sd_code_on_block"]


def test_monotonic_epoch_parse_and_compare() -> None:
    assert parse_synthesis_publication_epoch_seq_v1("syn-epoch-a-3") == 3
    out = compare_gp08_replay02_publication_monotonicity_v1(["syn-x-1", "syn-y-2", "syn-z-10"])
    assert out["gp08_replay02_monotonic_passed"] is True
    bad = compare_gp08_replay02_publication_monotonicity_v1(["syn-x-5", "syn-x-2"])
    assert bad["gp08_replay02_monotonic_passed"] is False


def test_monotonic_assert_rejects_regression() -> None:
    with pytest.raises(SynthesisPublicationError, match="publication_epoch_not_monotonic"):
        assert_publication_epoch_monotonic_v1(prior_epoch="syn-ep-3", next_epoch="syn-ep-2")


@pytest.mark.parametrize(
    "verifier",
    [
        verify_gp08_pub01_publication_barrier_module_static,
        verify_gp08_replay02_publication_epoch_forward_only_static,
    ],
)
def test_static_gates(verifier: object) -> None:
    out = verifier()  # type: ignore[operator]
    assert out["passed"] is True


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8pub-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Pub")
    tenant = Tenant(
        company_name="P8PUB",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8pub-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_publish_epoch_monotonic_and_empty_scope(db_session: Session) -> None:
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        publish_retrieval_index_epoch_v1,
    )

    tenant_id = _tenant(db_session)
    index_epoch = f"idx-{uuid.uuid4().hex[:6]}"
    publish_retrieval_index_epoch_v1(db_session, tenant_id=tenant_id, index_epoch=index_epoch)

    first = publish_synthesis_epoch_v1(
        db_session,
        tenant_id=tenant_id,
        published_index_epoch=index_epoch,
        allow_empty_scope=True,
    )
    second = publish_synthesis_epoch_v1(
        db_session,
        tenant_id=tenant_id,
        published_index_epoch=index_epoch,
        allow_empty_scope=True,
    )
    assert parse_synthesis_publication_epoch_seq_v1(str(second["synthesis_publication_epoch"])) > (
        parse_synthesis_publication_epoch_seq_v1(str(first["synthesis_publication_epoch"]))
    )

    status = build_synthesis_publication_status_v1(db_session, tenant_id=tenant_id)
    assert status["gp08_replay02_monotonic"] is True
    assert status["synthesis_publication_epoch"] == second["synthesis_publication_epoch"]


@pytest.mark.integration
def test_publish_blocks_forbidden_legality(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    job = CortexSynthesisJob(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        status="completed",
        envelope_json={"schema_version": 1, "retrieval_pins": {}},
        envelope_digest="sha256:" + "a" * 64,
        synthesis_workload_class="degradation_brief",
        synthesis_intent="inspect",
        execution_partition="authoritative",
        synthesis_policy_pack_id="SynthesisPolicyPackV1_Default",
        synthesis_orchestrator_build_id="syn-orchestrator-v1-stub",
        synthesis_legality_class="synthesis_forbidden",
        synthesis_job_replay_identity="sjri:test",
    )
    artifact = CortexSynthesisArtifact(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job.id,
        artifact_kind="degradation_brief",
        artifact_digest="sha256:" + "b" * 64,
        synthesis_legality_class="synthesis_forbidden",
        published=False,
        body_json={"synthesis_job_replay_identity": "sjri:test"},
    )
    db_session.add_all([job, artifact])
    db_session.flush()

    ev = evaluate_artifact_publish_eligibility_v1(
        db_session,
        tenant_id=tenant_id,
        artifact=artifact,
        job=job,
    )
    assert ev["eligible"] is False
    assert ev["sd_code"] == SD_PUBLISH_BLOCKED_V1

    with pytest.raises(SynthesisPublicationError, match="publish_requires_artifact"):
        publish_synthesis_epoch_v1(
            db_session,
            tenant_id=tenant_id,
            artifact_ids=[artifact.id],
        )


@pytest.mark.integration
def test_retract_marks_unpublished(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    job = CortexSynthesisJob(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        status="completed",
        envelope_json={},
        envelope_digest="sha256:" + "c" * 64,
        synthesis_workload_class="degradation_brief",
        synthesis_intent="inspect",
        execution_partition="authoritative",
        synthesis_policy_pack_id="SynthesisPolicyPackV1_Default",
        synthesis_orchestrator_build_id="syn-orchestrator-v1-stub",
        synthesis_legality_class="synthesis_replay_safe",
    )
    artifact = CortexSynthesisArtifact(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job.id,
        artifact_kind="degradation_brief",
        artifact_digest="sha256:" + "d" * 64,
        synthesis_legality_class="synthesis_replay_safe",
        published=True,
        synthesis_publication_epoch="syn-legacy-1",
        body_json={},
    )
    db_session.add_all([job, artifact])
    db_session.flush()
    out = retract_synthesis_artifact_v1(
        db_session,
        tenant_id=tenant_id,
        artifact_id=artifact.id,
        reason="test_retract",
    )
    assert out["retracted"] is True
    db_session.refresh(artifact)
    assert artifact.published is False
    assert artifact.body_json.get("retracted") is True
    assert artifact.synthesis_publication_epoch == "syn-legacy-1"
