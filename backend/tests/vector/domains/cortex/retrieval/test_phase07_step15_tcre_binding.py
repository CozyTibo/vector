"""P07-15 — TCRE / chronology / edge bindings (``retrieval.retrieval_tcre_binding``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.chronology_legality import (
    TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
)
from vector.domains.cortex.retrieval.phase_boundaries import RETRIEVAL_RD_TCRE_GAP_V1
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)
from vector.domains.cortex.retrieval.retrieval_tcre_binding import (
    GP07_TCRE01_GATE_ID_V1,
    PHASE07_RETRIEVAL_TCRE_BINDING_RUNTIME_SCHEMA_VERSION,
    apply_retrieval_tcre_binding_to_query_v1,
    build_retrieval_tcre_binding_catalog_v1,
    build_tcre_handoff_lookup_map_v1,
    list_tcre_coverage_gap_omissions_v1,
    map_runtime02_ref_to_retrieval_lookup_id_v1,
    materialize_retrieval_index_from_tcre_job_v1,
    parse_runtime02_operator_retrieval_ref_v1,
    verify_gp07_tcre01_runtime02_lookup_map_static,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_artifact import (
    CortexTcreReconstructionArtifact,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-runtime-architecture.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_phase07_tcre_binding_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_TCRE_BINDING_RUNTIME_SCHEMA_VERSION >= 1


def test_gp07_tcre01_static_gate() -> None:
    out = verify_gp07_tcre01_runtime02_lookup_map_static()
    assert out["passed"] is True
    assert out["id"] == GP07_TCRE01_GATE_ID_V1


def test_runtime02_lookup_map_deterministic() -> None:
    replay = "replay-deterministic"
    mid = "mat-001"
    a = map_runtime02_ref_to_retrieval_lookup_id_v1(
        ref_kind="materialization_id", ref_value=mid, replay_identity=replay
    )
    b = map_runtime02_ref_to_retrieval_lookup_id_v1(
        ref_kind="chronology_window_ref", ref_value=mid, replay_identity=replay
    )
    assert a == b
    assert parse_runtime02_operator_retrieval_ref_v1(f"chronology:{mid}") == (
        "materialization_id",
        mid,
    )


def test_coverage_gap_emits_rd_tcre_gap() -> None:
    rows = list_tcre_coverage_gap_omissions_v1(
        upstream_triggers={"reconstruction_coverage_gap": True},
        job=None,
        bind_required=False,
    )
    assert rows[0]["retrieval_omission_class"] == RETRIEVAL_RD_TCRE_GAP_V1


def test_tcre_binding_catalog() -> None:
    cat = build_retrieval_tcre_binding_catalog_v1()
    assert cat["gate_id"] == GP07_TCRE01_GATE_ID_V1
    assert "materialization_id" in cat["runtime02_ref_kinds"]


def test_doctrine_and_golden_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-runtime-architecture.md").read_text(
        encoding="utf-8"
    )
    assert "TCRE" in text
    golden = (
        Path(__file__).parent
        / "retrieval_golden_vectors"
        / "v1"
        / "cases"
        / "tcre"
        / "binding_lookup_map_v1"
        / "case.json"
    )
    assert golden.is_file()


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7tcre-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 TCRE")
    tenant = Tenant(
        company_name="P7TCRE",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7tcre-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _completed_tcre_job(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    chain_id: str,
    mat_id: str,
    edge_id: str,
) -> CortexTcreReconstructionJob:
    job = CortexTcreReconstructionJob(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_kind="reconstruction",
        status="completed",
        dry_run=False,
        scope_json={"materialization_ids": [mat_id]},
        summary_json={"replay_identity": "replay-tcre-job"},
        tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
        reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
        engine_build_ref="test-runtime",
    )
    db_session.add(job)
    db_session.flush()
    artifacts = [
        CortexTcreReconstructionArtifact(
            job_id=job.id,
            tenant_id=tenant_id,
            artifact_kind="chronology_receipt",
            artifact_key=mat_id,
            artifact_digest="digest-chron",
            body_json={
                "chronology_legality_class": "chronology_strict",
                "receipt_body": {},
                "snapshot": {},
            },
        ),
        CortexTcreReconstructionArtifact(
            job_id=job.id,
            tenant_id=tenant_id,
            artifact_kind="causal_edge",
            artifact_key=edge_id,
            artifact_digest=edge_id,
            body_json={
                "tcre_causal_edge_kind": "tcre_temporal_successor",
                "causal_legality_class": "causal_replay_equivalent",
                "parent_artifact_ids": [f"mat:{mat_id}"],
            },
        ),
        CortexTcreReconstructionArtifact(
            job_id=job.id,
            tenant_id=tenant_id,
            artifact_kind="causal_chain",
            artifact_key=chain_id,
            artifact_digest=chain_id,
            body_json={
                "causal_chain_id": chain_id,
                "causal_legality_class": "causal_replay_equivalent",
            },
        ),
    ]
    db_session.add_all(artifacts)
    db_session.flush()
    job.artifacts = artifacts
    return job


@pytest.mark.integration
def test_tcre_handoff_lookup_map_from_job(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    chain_id = f"chain-{uuid.uuid4().hex[:8]}"
    mat_id = str(uuid.uuid4())
    edge_id = f"edge-{uuid.uuid4().hex[:8]}"
    job = _completed_tcre_job(
        db_session,
        tenant_id=tenant_id,
        chain_id=chain_id,
        mat_id=mat_id,
        edge_id=edge_id,
    )
    lookup = build_tcre_handoff_lookup_map_v1(
        job=job,
        artifacts=list(job.artifacts),
        replay_identity="replay-tcre-job",
    )
    assert chain_id in lookup["by_causal_chain_id"]
    assert mat_id in lookup["by_materialization_id"]
    assert edge_id in lookup["by_tcre_causal_edge_id"]
    assert lookup["by_causal_chain_id"][chain_id]["retrieval_chain_ref"] == f"chain:{chain_id}"
    assert lookup["replay_artifact_pins"]


@pytest.mark.integration
def test_materialize_index_from_tcre_job_and_query(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    chain_id = f"chain-{uuid.uuid4().hex[:8]}"
    mat_id = str(uuid.uuid4())
    edge_id = f"edge-{uuid.uuid4().hex[:8]}"
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    job = _completed_tcre_job(
        db_session,
        tenant_id=tenant_id,
        chain_id=chain_id,
        mat_id=mat_id,
        edge_id=edge_id,
    )
    job.summary_json = {**dict(job.summary_json or {}), "replay_identity": replay}
    materialize_retrieval_index_from_tcre_job_v1(
        db_session,
        tenant_id=tenant_id,
        job=job,
        replay_identity=replay,
        index_epoch=epoch,
    )
    db_session.commit()
    index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=chain_id,
        replay_identity=replay,
        traversal_epoch=epoch,
        tcre_reconstruction_job_id=job.id,
    )
    db_session.commit()
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "addressing": {"causal_chain_id": chain_id},
            "replay_pins": {
                "replay_identity": replay,
                "index_epoch": epoch,
                "tcre_policy_bundle_digest": TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
                "tcre_reconstruction_job_id": str(job.id),
            },
        },
    )
    assert out.get("tcre_binding_envelope", {}).get("bind_state") == "bound"
    assert out.get("chronology_legality_class") == "strict"
    assert out.get("causal_legality_class") == "verified"
    assert not any(
        o.get("retrieval_omission_class") == RETRIEVAL_RD_TCRE_GAP_V1
        for o in (out.get("omissions") or [])
        if isinstance(o, dict)
    )


@pytest.mark.integration
def test_missing_tcre_job_emits_rd_tcre_gap(db_session: Session) -> None:
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
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "workload_class": "causal_chain",
            "addressing": {"causal_chain_id": chain},
            "replay_pins": {
                "replay_identity": replay,
                "index_epoch": epoch,
                "tcre_policy_bundle_digest": TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
                "tcre_reconstruction_job_id": str(uuid.uuid4()),
            },
        },
    )
    assert any(
        o.get("retrieval_omission_class") == RETRIEVAL_RD_TCRE_GAP_V1
        for o in (out.get("omissions") or [])
        if isinstance(o, dict)
    )
