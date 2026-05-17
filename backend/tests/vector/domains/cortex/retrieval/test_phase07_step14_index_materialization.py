"""P07-14 — Retrieval index materialization (``retrieval.retrieval_index_materialization``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_ingress import (
    RETRIEVAL_RD_INDEX_STALE_V1,
    RetrievalIngressError,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    GP07_IDX01_GATE_ID_V1,
    GP07_REPLAY02_GATE_ID_V1,
    PHASE07_RETRIEVAL_INDEX_MATERIALIZATION_RUNTIME_SCHEMA_VERSION,
    RetrievalIndexMaterializationError,
    assert_index_epoch_published_for_read_v1,
    build_retrieval_index_catalog_v1,
    compare_gp07_replay_02_index_permutation_v1,
    compute_index_lag_epochs_v1,
    materialize_retrieval_index_entry_v1,
    publish_retrieval_index_epoch_v1,
    run_retrieval_index_rebuild_v1,
    start_retrieval_index_build_v1,
    transition_retrieval_index_build_v1,
    verify_gp07_idx01_publish_barrier_static,
    verify_gp07_replay02_index_permutation_invariance_static,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-runtime-architecture.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_phase07_index_materialization_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_INDEX_MATERIALIZATION_RUNTIME_SCHEMA_VERSION >= 1


def test_index_build_illegal_transition_raises() -> None:
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        validate_index_build_state_transition_v1,
    )

    with pytest.raises(RetrievalIndexMaterializationError, match="index_build_illegal_transition"):
        validate_index_build_state_transition_v1(from_state="QUEUED", to_state="PUBLISHED")


def test_gp07_idx01_static_gate() -> None:
    out = verify_gp07_idx01_publish_barrier_static()
    assert out["passed"] is True
    assert out["id"] == GP07_IDX01_GATE_ID_V1


def test_gp07_replay02_static_gate() -> None:
    out = verify_gp07_replay02_index_permutation_invariance_static()
    assert out["passed"] is True
    assert out["id"] == GP07_REPLAY02_GATE_ID_V1


def test_replay02_compare_identical() -> None:
    payload = {
        "hits": [{"retrieval_lookup_id": "sha256:" + "d" * 64}],
        "retrieval_query_replay_identity": "e" * 64,
    }
    out = compare_gp07_replay_02_index_permutation_v1(payload, dict(payload))
    assert out["gp07_replay_02_passed"] is True


def test_index_catalog() -> None:
    cat = build_retrieval_index_catalog_v1()
    assert cat["ret_idx01_gate_id"] == GP07_IDX01_GATE_ID_V1


def test_doctrine_and_fixture_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-runtime-architecture.md").read_text(
        encoding="utf-8"
    )
    assert "RET-IDX-01" in text or "RET‑IDX‑01" in text
    assert (root / "DOCS" / "cortex" / "retrieval" / "fixtures" / "RetrievalPolicyPackV1_Default.json").is_file()
    golden = (
        Path(__file__).parent
        / "retrieval_golden_vectors"
        / "v1"
        / "cases"
        / "index"
        / "publish_barrier_v1"
        / "case.json"
    )
    assert golden.is_file()


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7idx-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Idx")
    tenant = Tenant(
        company_name="P7IDX",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7idx-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_publish_barrier_blocks_unpublished_read(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    epoch = f"epoch-unpub-{uuid.uuid4().hex[:6]}"
    job = start_retrieval_index_build_v1(db_session, tenant_id=tenant_id, index_epoch=epoch)
    transition_retrieval_index_build_v1(db_session, epoch_row=job, to_state="BUILDING")
    row = materialize_retrieval_index_entry_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id="chain-1",
        replay_identity="replay-1",
        index_epoch=epoch,
        auto_publish=False,
    )
    db_session.commit()
    with pytest.raises(RetrievalIngressError) as exc:
        assert_index_epoch_published_for_read_v1(
            db_session,
            tenant_id=tenant_id,
            index_epoch_on_row=row.index_epoch,
        )
    assert exc.value.code == RETRIEVAL_RD_INDEX_STALE_V1


@pytest.mark.integration
def test_materialize_publish_and_query(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    chain = f"chain-{uuid.uuid4().hex[:8]}"
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=chain,
        replay_identity=replay,
        traversal_epoch=epoch,
    )
    db_session.commit()
    lag = compute_index_lag_epochs_v1(db_session, tenant_id=tenant_id)
    assert lag["published_index_epoch"] == epoch
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "addressing": {"causal_chain_id": chain},
            "replay_pins": {
                "replay_identity": replay,
                "index_epoch": epoch,
                "tcre_policy_bundle_digest": "sha256:policy",
            },
        },
    )
    assert out.get("published_index_epoch") == epoch
    assert "index_lag_epochs" in out


@pytest.mark.integration
def test_index_rebuild_admin_flow(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    job = start_retrieval_index_build_v1(db_session, tenant_id=tenant_id, index_epoch="epoch-rebuild-1")
    job = transition_retrieval_index_build_v1(db_session, epoch_row=job, to_state="BUILDING")
    materialize_retrieval_index_entry_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id="c-rebuild",
        replay_identity="r-rebuild",
        index_epoch=job.index_epoch,
        auto_publish=False,
    )
    published = publish_retrieval_index_epoch_v1(
        db_session, tenant_id=tenant_id, index_epoch=job.index_epoch
    )
    db_session.commit()
    assert published.build_state == "PUBLISHED"
    result = run_retrieval_index_rebuild_v1(
        db_session, tenant_id=tenant_id, index_epoch=f"epoch-rebuild-{uuid.uuid4().hex[:4]}"
    )
    assert result["build_state"] == "PUBLISHED"
