"""P07-19 — Degradation taxonomy + propagation (``retrieval.retrieval_degradation_taxonomy``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_bounded_caps import RETRIEVAL_RD_CODES_REGISTRY_V1
from vector.domains.cortex.retrieval.retrieval_degradation_taxonomy import (
    GP07_DEG02_GATE_ID_V1,
    GP07_DEG03_GATE_ID_V1,
    PHASE07_RETRIEVAL_DEGRADATION_TAXONOMY_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_SUBSTRATE_PROPAGATION_ROWS_V1,
    RetrievalDegradationTaxonomyError,
    build_degradation_propagation_chain_v1,
    build_retrieval_degradation_topology_catalog_v1,
    build_retrieval_rd_rollup_v1,
    propagate_upstream_triggers_to_rd_omissions_v1,
    validate_retrieval_completeness_uses_rd_registry_v1,
    validate_retrieval_hit_multiset_monotonic_extension_v1,
    validate_retrieval_omission_multiset_monotonic_extension_v1,
    verify_gp07_deg02_monotonicity_static,
    verify_gp07_deg03_propagation_table_static,
    verify_gp07_deg04_completeness_registry_static,
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


def test_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_DEGRADATION_TAXONOMY_RUNTIME_SCHEMA_VERSION >= 1


def test_substrate_propagation_table_covers_doctrine_codes() -> None:
    codes = {row["consequence_code"] for row in RETRIEVAL_SUBSTRATE_PROPAGATION_ROWS_V1}
    assert "RD-TCRE-GAP" in codes
    assert "RD-GRAPH-ORPHAN" in codes
    assert "RD-TRAVERSAL-BLOCKED" in codes
    for code in codes:
        assert code in RETRIEVAL_RD_CODES_REGISTRY_V1


def test_propagate_upstream_triggers() -> None:
    rows = propagate_upstream_triggers_to_rd_omissions_v1(
        {
            "reconstruction_coverage_gap": True,
            "orphan_artifacts": True,
            "pending_link_candidates": True,
        }
    )
    rd = {r["retrieval_omission_class"] for r in rows}
    assert "RD-TCRE-GAP" in rd
    assert "RD-GRAPH-ORPHAN" in rd
    assert "RD-TRAVERSAL-BLOCKED" in rd


def test_propagation_chain_explanations() -> None:
    chain = build_degradation_propagation_chain_v1(
        upstream_triggers={"traversal_never_executed": True}
    )
    assert len(chain) == 1
    assert chain[0]["consequence_code"] == "RD-TRAVERSAL-IDLE"
    assert "explanation_summary" in chain[0]


def test_ret_deg02_monotonicity() -> None:
    hits_before = [{"retrieval_lookup_id": "sha256:" + "a" * 64}]
    hits_after = hits_before + [{"retrieval_lookup_id": "sha256:" + "b" * 64}]
    validate_retrieval_hit_multiset_monotonic_extension_v1(hits_before, hits_after)
    with pytest.raises(RetrievalDegradationTaxonomyError, match="hit_multiset_regression"):
        validate_retrieval_hit_multiset_monotonic_extension_v1(hits_after, hits_before)
    om_before = [{"retrieval_omission_class": "RD-CAP-HITS"}]
    om_after = om_before + [{"retrieval_omission_class": "RD-TCRE-GAP"}]
    validate_retrieval_omission_multiset_monotonic_extension_v1(om_before, om_after)


def test_rd_rollup() -> None:
    rollup = build_retrieval_rd_rollup_v1(
        [
            {"retrieval_omission_class": "RD-CAP-HITS"},
            {"retrieval_omission_class": "RD-CAP-HITS"},
            {"retrieval_omission_class": "RD-TCRE-GAP"},
        ]
    )
    assert rollup["rd_code_counts"]["RD-CAP-HITS"] == 2
    assert rollup["rd_code_total"] == 3


def test_completeness_registry_validation() -> None:
    validate_retrieval_completeness_uses_rd_registry_v1(
        {"omission_classes": {"RD-LINEAGE-GAP": 1}}
    )
    with pytest.raises(RetrievalDegradationTaxonomyError):
        validate_retrieval_completeness_uses_rd_registry_v1(
            {"omission_classes": {"RD-NOT-A-CODE": 1}}
        )


def test_static_gates() -> None:
    assert verify_gp07_deg02_monotonicity_static()["passed"] is True
    assert verify_gp07_deg02_monotonicity_static()["id"] == GP07_DEG02_GATE_ID_V1
    assert verify_gp07_deg03_propagation_table_static()["passed"] is True
    assert verify_gp07_deg03_propagation_table_static()["id"] == GP07_DEG03_GATE_ID_V1
    assert verify_gp07_deg04_completeness_registry_static()["passed"] is True


def test_degradation_topology_catalog() -> None:
    cat = build_retrieval_degradation_topology_catalog_v1(tenant_id="t1")
    assert cat["tenant_id"] == "t1"
    assert len(cat["substrate_propagation_table"]) >= 6
    assert "RD-TCRE-GAP" in cat["rd_codes_registry"]


def test_doctrine_present() -> None:
    text = (
        _repo_root() / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-degradation-taxonomy.md"
    ).read_text(encoding="utf-8")
    assert "RD-CAP-HITS" in text
    assert "RET-DEG-02" in text or "RET‑DEG‑02" in text


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7deg-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Deg")
    tenant = Tenant(
        company_name="P7DEG",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7deg-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_query_includes_degradation_topology_fields(db_session: Session) -> None:
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
            "addressing": {"causal_chain_id": chain},
            "replay_pins": {
                "replay_identity": replay,
                "index_epoch": epoch,
                "tcre_policy_bundle_digest": "sha256:policy",
                "octs_engine_build_ref": "build-stub",
            },
            "upstream_triggers": {"orphan_artifacts": True},
        },
    )
    assert "retrieval_rd_rollup" in out
    assert out["retrieval_rd_rollup"]["rd_code_counts"].get("RD-GRAPH-ORPHAN", 0) >= 1
    chain_rows = out.get("degradation_propagation_chain") or []
    assert any(r.get("consequence_code") == "RD-GRAPH-ORPHAN" for r in chain_rows)
