"""P07-10 — Provenance + evidence envelope (``retrieval.retrieval_provenance_evidence``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_provenance_evidence import (
    GP07_PROV01_GATE_ID_V1,
    PHASE07_RETRIEVAL_PROVENANCE_EVIDENCE_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_EVIDENCE_LEGALITY_CLASSES_V1,
    RETRIEVAL_PROVENANCE_ENVELOPE_REQUIRED_FIELDS_V1,
    RetrievalProvenanceEvidenceError,
    build_retrieval_evidence_hit_v1,
    build_retrieval_provenance_envelope_v1,
    build_retrieval_provenance_inspector_catalog_v1,
    classify_evidence_legality_class_v1,
    compute_provenance_coverage_percent_v1,
    list_ret_prov01_missing_upstream_digests_v1,
    normalize_retrieval_omission_rows_v1,
    validate_retrieval_provenance_envelope_v1,
    verify_gp07_prov01_provenance_field_checklist_static,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-provenance-evidence-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_phase07_provenance_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_PROVENANCE_EVIDENCE_RUNTIME_SCHEMA_VERSION >= 1


def test_provenance_envelope_required_fields_and_id() -> None:
    env = build_retrieval_provenance_envelope_v1(
        tenant_id=uuid.UUID(int=0),
        replay_posture="stable",
        evidence_legality_class="evidence_authoritative",
        upstream_digests={"retrieval_index_entry_digest": "a" * 64},
    )
    for field in RETRIEVAL_PROVENANCE_ENVELOPE_REQUIRED_FIELDS_V1:
        assert field in env
    assert len(str(env["provenance_envelope_id"])) == 64
    validate_retrieval_provenance_envelope_v1(env)


def test_invalid_envelope_raises() -> None:
    with pytest.raises(RetrievalProvenanceEvidenceError, match="provenance_envelope_missing_fields"):
        validate_retrieval_provenance_envelope_v1({"schema_version": 1})


def test_ret_prov01_missing_causal_chain_id() -> None:
    missing = list_ret_prov01_missing_upstream_digests_v1(
        workload_class="causal_chain",
        upstream_digests={"retrieval_index_entry_digest": "b" * 64},
    )
    assert "causal_chain_id" in missing


def test_classify_evidence_degraded_on_prov01_floor() -> None:
    ev = classify_evidence_legality_class_v1(
        chronology_legality_class="strict",
        causal_legality_class="verified",
        replay_posture="stable",
        execution_partition="authoritative",
        prov01_degraded_floor=True,
    )
    assert ev == "evidence_degraded"


def test_omission_rows_semantics_ret_prov02() -> None:
    rows = normalize_retrieval_omission_rows_v1(
        [{"retrieval_omission_class": "RD-CAP-HITS", "upstream_trigger": "policy"}]
    )
    assert rows[0]["omission_semantics"] == "omitted_cap"
    partial = normalize_retrieval_omission_rows_v1([], partial_addressing=True)
    assert any(r["omission_semantics"] == "omitted_addressing_partial" for r in partial)


def test_provenance_coverage_percent() -> None:
    hits = [
        {
            "evidence_legality_class": "evidence_authoritative",
            "provenance": {"provenance_envelope_id": "c" * 64},
        }
    ]
    assert compute_provenance_coverage_percent_v1(hits) == 100
    assert compute_provenance_coverage_percent_v1([]) == 0


def test_gp07_prov01_static_gate() -> None:
    out = verify_gp07_prov01_provenance_field_checklist_static()
    assert out["passed"] is True
    assert out["id"] == GP07_PROV01_GATE_ID_V1


def test_inspector_catalog() -> None:
    cat = build_retrieval_provenance_inspector_catalog_v1()
    assert cat["gate_id"] == GP07_PROV01_GATE_ID_V1
    assert set(cat["evidence_legality_classes"]) == set(RETRIEVAL_EVIDENCE_LEGALITY_CLASSES_V1)


def test_doctrine_file_present() -> None:
    text = (
        _repo_root()
        / "DOCS"
        / "cortex"
        / "retrieval"
        / "phase-07-retrieval-provenance-evidence-doctrine.md"
    ).read_text(encoding="utf-8")
    assert "RET-PROV-01" in text or "RET‑PROV‑01" in text
    assert "RetrievalProvenanceEnvelopeV1" in text


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7prov-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Prov")
    tenant = Tenant(
        company_name="P7PROV",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7prov-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_query_execution_emits_provenance_hits(db_session: Session) -> None:
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
    hits = out.get("retrieval_evidence_hits") or out.get("hits") or []
    assert len(hits) >= 1
    hit = hits[0]
    assert hit.get("provenance", {}).get("provenance_envelope_id")
    assert hit.get("evidence_legality_class") in RETRIEVAL_EVIDENCE_LEGALITY_CLASSES_V1
    assert "provenance_coverage_percent" in out
    assert out["ingress_provenance"].get("provenance_envelope_id")


def test_build_evidence_hit_from_row_stub() -> None:
    class _Row:
        chronology_legality_class = "strict"
        causal_legality_class = "verified"
        continuity_posture = "stable"
        traversal_epoch = "e1"
        artifact_ref_json = {"causal_chain_id": "chain-x"}
        index_kind = "causal_chain"
        index_key = "causal_chain:chain-x"
        replay_identity = "rid"
        retrieval_policy_digest = "d" * 64

    hit = build_retrieval_evidence_hit_v1(
        tenant_id=uuid.UUID(int=0),
        retrieval_lookup_id="sha256:" + "f" * 64,
        row=_Row(),
        replay_posture="stable",
        workload_class="causal_chain",
        execution_partition="authoritative",
        replay_pins={"tcre_policy_bundle_digest": "sha256:policy"},
        replay_identity_match=True,
    )
    validate_retrieval_provenance_envelope_v1(hit["provenance"])
    assert hit["ret_prov01_missing_digests"] == []
