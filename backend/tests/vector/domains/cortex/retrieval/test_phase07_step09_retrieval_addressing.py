"""P07-09 — Retrieval addressing model (``retrieval.retrieval_addressing``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.query_execution import (
    RETRIEVAL_QUERY_ADDRESSING_UNRESOLVED_CODE_V1,
    RetrievalQueryExecutionError,
    resolve_retrieval_lookup_id_from_addressing_v1,
)
from vector.domains.cortex.retrieval.retrieval_addressing import (
    GP07_ADDR01_GATE_ID_V1,
    PHASE07_RETRIEVAL_ADDRESSING_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_CANON_VERSION_V1,
    assess_partial_addressing_v1,
    build_retrieval_addressing_catalog_v1,
    build_retrieval_chain_ref_body_v1,
    build_retrieval_lookup_canon_body_v1,
    compute_retrieval_lookup_id_from_canon_body_v1,
    load_retrieval_golden_case_v1,
    resolve_retrieval_addressing_v1,
    retrieval_golden_vectors_v1_root,
    run_retrieval_golden_addressing_case_v1,
    verify_gp07_addr01_golden_corpus_static,
)
from vector.domains.cortex.retrieval.retrieval_lookup_projection import (
    derive_retrieval_lookup_id_v1,
    format_retrieval_lookup_id_v1,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        if (root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-addressing-model.md").is_file():
            return root
    pytest.fail("repo root not found")


def test_phase07_addressing_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_ADDRESSING_RUNTIME_SCHEMA_VERSION >= 1


def test_lookup_id_format_sha256_prefix() -> None:
    digest = "a" * 64
    lid = format_retrieval_lookup_id_v1(digest)
    assert lid == f"sha256:{digest}"
    assert len(lid) == 71


def test_derive_lookup_id_stable_and_formatted() -> None:
    a = derive_retrieval_lookup_id_v1(
        index_kind="causal_chain",
        index_key="causal_chain:abc",
        replay_identity="rid1",
    )
    b = derive_retrieval_lookup_id_v1(
        index_kind="causal_chain",
        index_key="causal_chain:abc",
        replay_identity="rid1",
    )
    assert a == b
    assert a.startswith("sha256:")
    assert len(a) == 71


def test_resolve_direct_lookup_id() -> None:
    full_id = "sha256:" + "b" * 64
    env = {
        "tenant_id": str(uuid.UUID(int=0)),
        "workload_class": "causal_chain",
        "intent": "inspect",
        "addressing": {"retrieval_lookup_id": full_id},
    }
    res = resolve_retrieval_addressing_v1(env, tenant_id=uuid.UUID(int=0))
    assert res.retrieval_lookup_id == full_id
    assert res.resolution_path == "direct_retrieval_lookup_id"


def test_resolve_legacy_causal_chain() -> None:
    env = {
        "tenant_id": str(uuid.UUID(int=1)),
        "workload_class": "causal_chain",
        "intent": "inspect",
        "addressing": {"causal_chain_id": "chain-1"},
        "replay_pins": {"replay_identity": "replay-1"},
    }
    res = resolve_retrieval_addressing_v1(env, tenant_id=uuid.UUID(int=1))
    assert res.resolution_path == "legacy_index_causal_chain"
    want = derive_retrieval_lookup_id_v1(
        index_kind="causal_chain",
        index_key="causal_chain:chain-1",
        replay_identity="replay-1",
    )
    assert res.retrieval_lookup_id == want


def test_compose_canon_deterministic() -> None:
    body = build_retrieval_lookup_canon_body_v1(
        tenant_id="t1",
        workload_class="chronology_window",
        primary_address=build_retrieval_chain_ref_body_v1(causal_chain_id="x"),
        temporal_scope={"t_as_of_unix_ns": 1},
        replay_pins={"index_epoch": "e1"},
    )
    assert body["canon_version"] == RETRIEVAL_CANON_VERSION_V1
    id1 = compute_retrieval_lookup_id_from_canon_body_v1(body)
    id2 = compute_retrieval_lookup_id_from_canon_body_v1(body)
    assert id1 == id2


def test_partial_addressing_assessment() -> None:
    partial, missing = assess_partial_addressing_v1(
        {"causal_chain_id": "x"},
        workload_class="causal_chain",
    )
    assert partial is True
    assert missing


def test_unresolved_raises() -> None:
    env = {
        "tenant_id": str(uuid.UUID(int=2)),
        "workload_class": "causal_chain",
        "intent": "inspect",
        "addressing": {},
    }
    with pytest.raises(RetrievalQueryExecutionError) as exc:
        resolve_retrieval_lookup_id_from_addressing_v1(env)
    assert exc.value.code == RETRIEVAL_QUERY_ADDRESSING_UNRESOLVED_CODE_V1


def test_addressing_catalog() -> None:
    cat = build_retrieval_addressing_catalog_v1()
    assert cat["gate_id"] == GP07_ADDR01_GATE_ID_V1
    assert "legacy_index_causal_chain" in cat["resolution_order"]


def test_verify_gp07_addr01_golden_corpus() -> None:
    out = verify_gp07_addr01_golden_corpus_static()
    assert out["passed"] is True
    assert retrieval_golden_vectors_v1_root().is_dir()


def test_doctrine_file_present() -> None:
    text = (
        _repo_root() / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-addressing-model.md"
    ).read_text(encoding="utf-8")
    assert "RET-ADDR-01" in text or "RET‑ADDR‑01" in text
    assert "retrieval_lookup_id" in text


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7addr-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Addr")
    tenant = Tenant(
        company_name="P7ADDR",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7addr-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_index_and_query_lookup_id_match(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    chain = f"chain-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=chain,
        replay_identity=replay,
        traversal_epoch="epoch-1",
    )
    db_session.commit()
    assert row.retrieval_lookup_id.startswith("sha256:")
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "addressing": {"causal_chain_id": chain},
            "replay_pins": {
                "replay_identity": replay,
                "index_epoch": "epoch-1",
                "tcre_policy_bundle_digest": "sha256:policy",
            },
        },
    )
    assert out["retrieval_lookup_id"] == row.retrieval_lookup_id
    assert out["addressing_resolution"]["resolution_path"] == "legacy_index_causal_chain"


@pytest.mark.integration
def test_golden_causal_chain_case_runtime() -> None:
    case = run_retrieval_golden_addressing_case_v1(
        load_retrieval_golden_case_v1("query/causal_chain_minimal_v1")
    )
    assert case["resolution_path"] == "legacy_index_causal_chain"
