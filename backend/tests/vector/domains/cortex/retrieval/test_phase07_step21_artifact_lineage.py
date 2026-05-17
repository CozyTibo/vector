"""P07-21 — artifact lineage retrieval (``retrieval.retrieval_artifact_lineage``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.lineage.artifact_lineage_graph import persist_lineage_edge_v1
from vector.domains.cortex.lineage.lineage_chain_builder import build_artifact_lineage_chain_v1
from vector.domains.cortex.retrieval.retrieval_artifact_lineage import (
    GP07_LINEAGE01_GATE_ID_V1,
    PHASE07_RETRIEVAL_ARTIFACT_LINEAGE_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_RD_LINEAGE_GAP_V1,
    build_retrieval_lineage_explorer_catalog_v1,
    compute_lineage_coverage_v1,
    compute_node_hop_depths_v1,
    list_lineage_gap_omissions_v1,
    load_retrieval_lineage_golden_case_v1,
    run_retrieval_golden_lineage_explorer_case_v1,
    validate_lineage_chain_replay_pin_v1,
    verify_gp07_lineage01_golden_corpus_static,
    verify_gp07_lineage01_terminal_to_root_cap_static,
)
from vector.domains.cortex.retrieval.retrieval_bounded_caps import RETRIEVAL_RD_CODES_REGISTRY_V1
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


def test_phase07_artifact_lineage_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_ARTIFACT_LINEAGE_RUNTIME_SCHEMA_VERSION >= 1


def test_rd_lineage_gap_in_registry() -> None:
    assert RETRIEVAL_RD_LINEAGE_GAP_V1 in RETRIEVAL_RD_CODES_REGISTRY_V1


def test_gp07_lineage01_static_gates() -> None:
    assert verify_gp07_lineage01_terminal_to_root_cap_static()["passed"] is True
    assert verify_gp07_lineage01_golden_corpus_static()["passed"] is True
    assert verify_gp07_lineage01_terminal_to_root_cap_static()["id"] == GP07_LINEAGE01_GATE_ID_V1


def test_golden_lineage_explorer_case() -> None:
    case = load_retrieval_lineage_golden_case_v1("query/lineage_explorer_minimal_v1")
    result = run_retrieval_golden_lineage_explorer_case_v1(case)
    assert result["gp07_lineage01_passed"] is True
    assert result["lineage_coverage"] == "complete"


def test_lineage_gap_omissions_emitted() -> None:
    rows = list_lineage_gap_omissions_v1(upstream_trigger="test", truncated=True)
    assert rows[0]["retrieval_omission_class"] == RETRIEVAL_RD_LINEAGE_GAP_V1


def test_lineage_catalog() -> None:
    cat = build_retrieval_lineage_explorer_catalog_v1()
    assert cat["gate_id"] == GP07_LINEAGE01_GATE_ID_V1
    assert cat["golden_case_id"] == "query/lineage_explorer_minimal_v1"


def test_doctrine_and_golden_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-runtime-architecture.md").read_text(
        encoding="utf-8"
    )
    assert "Lineage" in text
    golden = (
        Path(__file__).parent
        / "retrieval_golden_vectors"
        / "v1"
        / "cases"
        / "query"
        / "lineage_explorer_minimal_v1"
        / "case.json"
    )
    assert golden.is_file()


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7lineage-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Lineage")
    tenant = Tenant(
        company_name="P7LINEAGE",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7lineage-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_lineage_explorer_workload_e2e(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    chain_id = f"chain-{uuid.uuid4().hex[:8]}"
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=chain_id,
        replay_identity=replay,
        traversal_epoch=epoch,
    )
    lookup_id = str(row.retrieval_lookup_id)
    persist_lineage_edge_v1(
        db_session,
        tenant_id=tenant_id,
        from_artifact_kind="tcre_chain",
        from_artifact_ref=chain_id,
        to_artifact_kind="retrieval_index",
        to_artifact_ref=lookup_id,
        edge_kind="tcre_binds_index",
        replay_identity=replay,
    )
    db_session.commit()
    chain = build_artifact_lineage_chain_v1(
        db_session,
        tenant_id=tenant_id,
        terminal_artifact_kind="retrieval_index",
        terminal_artifact_ref=lookup_id,
        max_hops=32,
    )
    digest = str(chain["lineage_chain_digest"])
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "workload_class": "lineage_explorer",
            "intent": "inspect",
            "addressing": {
                "retrieval_lookup_id": lookup_id,
                "artifact_kind": "retrieval_index",
                "artifact_ref": lookup_id,
            },
            "replay_pins": {
                "index_epoch": epoch,
                "lineage_chain_digest": digest,
                "tcre_policy_bundle_digest": "sha256:policy-stub",
                "octs_engine_build_ref": "build-stub",
            },
            "expected_replay_identity": replay,
            "selection_policy": {
                "max_hits": 64,
                "max_chronology_rows": 100,
                "max_edges": 50,
                "max_lineage_hops": 32,
            },
        },
    )
    assert out.get("workload_class") == "lineage_explorer"
    binding = out.get("lineage_binding_envelope")
    assert isinstance(binding, dict)
    assert binding.get("lineage_chain_digest") == digest
    assert binding.get("lineage_coverage") in ("complete", "partial")
    hits = out.get("hits") or []
    assert len(hits) >= 1
    assert all(isinstance(h, dict) and "lineage_hop_count" in h for h in hits)
    assert out.get("lineage_chain_digest") == digest
    lineage = out.get("lineage")
    assert isinstance(lineage, dict)
    assert lineage.get("lineage_chain_digest") == digest


@pytest.mark.integration
def test_lineage_digest_pin_mismatch_emits_gap(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=replay,
        traversal_epoch=epoch,
    )
    db_session.commit()
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "workload_class": "lineage_explorer",
            "intent": "inspect",
            "addressing": {"retrieval_lookup_id": row.retrieval_lookup_id},
            "replay_pins": {
                "index_epoch": epoch,
                "lineage_chain_digest": "sha256:wrong-pin",
                "tcre_policy_bundle_digest": "sha256:policy-stub",
                "octs_engine_build_ref": "build-stub",
            },
            "expected_replay_identity": replay,
            "selection_policy": {"max_hits": 64, "max_lineage_hops": 32},
        },
    )
    omissions = out.get("omissions") or []
    assert any(
        isinstance(o, dict) and o.get("retrieval_omission_class") == RETRIEVAL_RD_LINEAGE_GAP_V1
        for o in omissions
    )
    binding = out.get("lineage_binding_envelope")
    assert isinstance(binding, dict)
    assert binding.get("lineage_chain_digest_pin_match") is False


def test_replay_pin_helpers() -> None:
    chain = {
        "terminal": {"kind": "k", "ref": "r"},
        "nodes": [],
        "edges": [],
        "lineage_chain_digest": "sha256:abc",
    }
    ok, _ = validate_lineage_chain_replay_pin_v1({"lineage_chain_digest": "sha256:abc"}, chain)
    assert ok is True
    cov = compute_lineage_coverage_v1(chain, truncated=False, pin_match=True, edge_omissions=0)
    assert cov == "gap"
    depths = compute_node_hop_depths_v1(
        {
            "terminal": {"kind": "retrieval_index", "ref": "t"},
            "edges": [{"from": "a:1", "to": "retrieval_index:t"}],
        }
    )
    assert depths.get("retrieval_index:t") == 0
