"""P07-12 — Deterministic ranking + selection (``retrieval.retrieval_ranking_selection``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_ranking_selection import (
    GP07_RANK01_GATE_ID_V1,
    PHASE07_RETRIEVAL_RANKING_SELECTION_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_RD_CAP_HITS_V1,
    RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1,
    RetrievalRankingSelectionError,
    apply_retrieval_ranking_and_selection_v1,
    build_retrieval_ranking_selection_catalog_v1,
    enforce_selection_policy_rank01_v1,
    normalize_retrieval_selection_policy_v1,
    sort_hits_deterministically_v1,
    verify_gp07_rank01_no_float_scores_static,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-ranking-selection-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_phase07_ranking_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_RANKING_SELECTION_RUNTIME_SCHEMA_VERSION >= 1


def test_forbidden_selection_policy_keys() -> None:
    with pytest.raises(RetrievalRankingSelectionError, match="selection_policy_forbidden_rank_keys"):
        enforce_selection_policy_rank01_v1({"semantic_similarity": 1})


def test_normalize_selection_policy_includes_profile() -> None:
    caps = normalize_retrieval_selection_policy_v1(
        "causal_chain",
        {"selection_policy_profile_id": RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1},
    )
    assert caps["selection_policy_profile_id"] == RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1
    assert caps["max_hits"] >= 1


def test_sort_deterministic_authoritative_first() -> None:
    hits = [
        {
            "retrieval_lookup_id": "sha256:" + "b" * 64,
            "evidence_legality_class": "evidence_degraded",
            "provenance": {"replay_posture": "partial", "chronology_legality_class": "strict"},
        },
        {
            "retrieval_lookup_id": "sha256:" + "a" * 64,
            "evidence_legality_class": "evidence_authoritative",
            "provenance": {"replay_posture": "stable", "chronology_legality_class": "strict"},
        },
    ]
    sorted_hits = sort_hits_deterministically_v1(
        list(reversed(hits)),
        profile_id=RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1,
    )
    assert sorted_hits[0]["retrieval_lookup_id"] == "sha256:" + "a" * 64


def test_cap_truncation_emits_rd_cap_hits() -> None:
    hits = [
        {"retrieval_lookup_id": f"sha256:{i:064x}", "provenance": {}}
        for i in range(3)
    ]
    caps = normalize_retrieval_selection_policy_v1("causal_chain", {"max_hits": 1})
    out = apply_retrieval_ranking_and_selection_v1(hits=hits, caps=caps)
    assert len(out["hits"]) == 1
    assert any(o["retrieval_omission_class"] == RETRIEVAL_RD_CAP_HITS_V1 for o in out["omissions"])


def test_gp07_rank01_static_gate() -> None:
    out = verify_gp07_rank01_no_float_scores_static()
    assert out["passed"] is True
    assert out["id"] == GP07_RANK01_GATE_ID_V1


def test_ranking_catalog() -> None:
    cat = build_retrieval_ranking_selection_catalog_v1()
    assert cat["gate_id"] == GP07_RANK01_GATE_ID_V1
    assert RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1 in cat["selection_policy_profile_ids"]


def test_doctrine_file_present() -> None:
    text = (
        _repo_root()
        / "DOCS"
        / "cortex"
        / "retrieval"
        / "phase-07-retrieval-ranking-selection-doctrine.md"
    ).read_text(encoding="utf-8")
    assert "RET-RANK-01" in text or "RET‑RANK‑01" in text
    assert "selection_policy_profile_id" in text or "G-P07-RANK-01" in text


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7rank-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Rank")
    tenant = Tenant(
        company_name="P7RANK",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7rank-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_query_execution_includes_selection_sort_trace(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    chain = f"chain-{uuid.uuid4().hex[:8]}"
    index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=chain,
        replay_identity=replay,
        traversal_epoch="epoch-1",
    )
    db_session.commit()
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
    assert "selection_sort_trace" in out
    assert out["selection_policy_profile_id"] == RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1
    trace = out["selection_sort_trace"]
    assert trace["selection_policy_profile_id"] == RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1
    assert len(trace.get("ranked_hits", [])) >= 1
