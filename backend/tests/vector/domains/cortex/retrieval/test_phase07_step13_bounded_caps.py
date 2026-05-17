"""P07-13 — Bounded caps + omission law (``retrieval.retrieval_bounded_caps``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_bounded_caps import (
    GP07_DEG01_GATE_ID_V1,
    PHASE07_RETRIEVAL_BOUNDED_CAPS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_POLICY_PACK_ID_DEFAULT_V1,
    RETRIEVAL_RD_CODES_REGISTRY_V1,
    RetrievalBoundedCapsError,
    apply_retrieval_policy_pack_defaults_v1,
    assert_retrieval_response_under_byte_cap_v1,
    assert_retrieval_wall_budget_v1,
    build_retrieval_omission_explorer_catalog_v1,
    build_retrieval_policy_pack_default_v1,
    classify_substrate_health_v1,
    enforce_cap_ceilings_not_bypassed_v1,
    load_retrieval_policy_pack_v1,
    normalize_retrieval_omission_law_rows_v1,
    retrieval_policy_pack_digest_v1,
    retrieval_policy_pack_fixture_path_v1,
    verify_gp07_deg01_rd_registry_closed_static,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-degradation-taxonomy.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_phase07_bounded_caps_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_BOUNDED_CAPS_RUNTIME_SCHEMA_VERSION >= 1


def test_policy_pack_fixture_loads() -> None:
    pack = load_retrieval_policy_pack_v1(retrieval_policy_pack_fixture_path_v1())
    assert pack["retrieval_policy_pack_id"] == RETRIEVAL_POLICY_PACK_ID_DEFAULT_V1
    assert pack["caps"]["max_hits"] == 100
    digest = retrieval_policy_pack_digest_v1(pack)
    assert len(digest) == 64


def test_cap_ceiling_bypass_rejected() -> None:
    with pytest.raises(RetrievalBoundedCapsError, match="selection_policy_cap_ceiling_exceeded"):
        enforce_cap_ceilings_not_bypassed_v1({"max_hits": 500})


def test_apply_policy_pack_defaults() -> None:
    caps = apply_retrieval_policy_pack_defaults_v1("causal_chain", {"max_hits": 25})
    assert caps["max_hits"] == 25
    assert caps["max_wall_ms"] == 30_000
    assert caps["retrieval_policy_pack_id"] == RETRIEVAL_POLICY_PACK_ID_DEFAULT_V1


def test_omission_law_registry() -> None:
    rows = normalize_retrieval_omission_law_rows_v1(
        [{"retrieval_omission_class": "RD-CAP-HITS", "upstream_trigger": "max_hits"}]
    )
    assert rows[0]["omission_semantics"] == "omitted_cap"
    with pytest.raises(RetrievalBoundedCapsError, match="unknown_retrieval_omission_class"):
        normalize_retrieval_omission_law_rows_v1([{"retrieval_omission_class": "RD-NOT-REAL"}])


def test_substrate_health_degraded_on_cap() -> None:
    health = classify_substrate_health_v1(
        omissions=[{"retrieval_omission_class": "RD-CAP-HITS"}],
        retrieval_legality_class="retrieval_degraded",
    )
    assert health == "degraded"


def test_413_response_too_large() -> None:
    with pytest.raises(RetrievalBoundedCapsError) as exc:
        assert_retrieval_response_under_byte_cap_v1(
            {"payload": "x" * 500},
            max_response_json_bytes=50,
        )
    assert exc.value.http_status == 413
    assert exc.value.code == "retrieval_response_too_large"


def test_503_timeout() -> None:
    with pytest.raises(RetrievalBoundedCapsError) as exc:
        assert_retrieval_wall_budget_v1(elapsed_ms=35_000, max_wall_ms=30_000)
    assert exc.value.http_status == 503
    assert exc.value.code == "retrieval_timeout"


def test_gp07_deg01_static_gate() -> None:
    out = verify_gp07_deg01_rd_registry_closed_static()
    assert out["passed"] is True
    assert out["id"] == GP07_DEG01_GATE_ID_V1


def test_omission_explorer_catalog() -> None:
    cat = build_retrieval_omission_explorer_catalog_v1()
    assert cat["gate_id"] == GP07_DEG01_GATE_ID_V1
    assert set(cat["rd_codes_registry"]) == set(RETRIEVAL_RD_CODES_REGISTRY_V1)


def test_doctrine_fixture_present() -> None:
    doc_fixture = _repo_root() / "DOCS" / "cortex" / "retrieval" / "fixtures" / "RetrievalPolicyPackV1_Default.json"
    assert doc_fixture.is_file()
    pack = build_retrieval_policy_pack_default_v1()
    assert pack["retrieval_policy_pack_id"] == RETRIEVAL_POLICY_PACK_ID_DEFAULT_V1


def test_doctrine_file_present() -> None:
    text = (
        _repo_root() / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-degradation-taxonomy.md"
    ).read_text(encoding="utf-8")
    assert "RD-CAP-HITS" in text
    assert "RET-DEG-01" in text or "RET‑DEG‑01" in text


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7cap-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Cap")
    tenant = Tenant(
        company_name="P7CAP",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7cap-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_query_response_includes_omission_law_fields(db_session: Session) -> None:
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
    assert out["retrieval_policy_pack_id"] == RETRIEVAL_POLICY_PACK_ID_DEFAULT_V1
    assert len(out.get("retrieval_policy_pack_digest", "")) == 64
    assert out.get("substrate_health_state") in ("healthy", "degraded", "critical", "unresolved", "replay_conflicted")
    assert "retrieval_omission_histogram" in out
