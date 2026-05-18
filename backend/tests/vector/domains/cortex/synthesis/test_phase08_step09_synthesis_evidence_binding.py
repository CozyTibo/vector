"""P08-09 — Cite-or-omit + citations (``synthesis.synthesis_evidence_binding``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_legality_matrix import SD_CITE_GAP_V1
from vector.domains.cortex.synthesis.synthesis_evidence_binding import (
    GP08_CITE01_GATE_ID_V1,
    PHASE08_SYNTHESIS_EVIDENCE_BINDING_RUNTIME_SCHEMA_VERSION,
    SD_SCOPE_EMPTY_V1,
    SYN_LAW_09_RULE_ID_V1,
    apply_syn_law_09_cite_or_omit_v1,
    bind_synthesis_evidence_v1,
    build_synthesis_citation_envelope_v1,
    build_synthesis_citation_law_catalog_v1,
    build_synthesis_citation_v1,
    build_synthesis_citations_from_hits_v1,
    verify_gp08_cite01_citation_schema_static,
    verify_gp08_cite01_cite_or_omit_static,
    verify_gp08_cite01_envelope_digest_stable_static,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _repo_root_containing_phase08_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-data-contracts.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/synthesis/ from test file parents.")


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8cite-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Cite User")
    tenant = Tenant(
        company_name="P8CITE",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8cite-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _sample_hit(lookup_suffix: str = "a") -> dict[str, object]:
    return {
        "retrieval_lookup_id": f"sha256:{lookup_suffix * 64}",
        "upstream_digest": "b" * 64,
        "evidence_legality_class": "verified",
        "provenance": {"artifact_kind": "tcre_chain", "artifact_ref": "chain-1"},
    }


def _legal_retrieval_with_hit() -> dict[str, object]:
    return {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-cite",
        "retrieval_evidence_hits": [_sample_hit()],
        "retrieval_omission_rows": [],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
    }


def test_phase08_evidence_binding_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_EVIDENCE_BINDING_RUNTIME_SCHEMA_VERSION >= 1


def test_build_synthesis_citation_v1_shape() -> None:
    citation = build_synthesis_citation_v1(hit=_sample_hit(), hit_index=0)
    assert citation["citation_id"] == "cite-0000"
    assert citation["hit_index"] == 0
    assert citation["hit_digest"].startswith("sha256:")


def test_syn_law_09_omits_uncited_claim() -> None:
    citations = build_synthesis_citations_from_hits_v1([_sample_hit()])
    accepted, omitted, sd = apply_syn_law_09_cite_or_omit_v1(
        [
            {
                "claim_id": "clm-0001",
                "claim_kind": "temporal_fact",
                "text": "ok",
                "citations": ["cite-0000"],
            },
            {
                "claim_id": "clm-0002",
                "claim_kind": "causal_link",
                "text": "no cites",
                "citations": [],
            },
        ],
        citations_by_id=citations,
    )
    assert len(accepted) == 1
    assert len(omitted) == 1
    assert any(r.get("sd_code") == SD_CITE_GAP_V1 for r in sd)


def test_bind_synthesis_evidence_empty_scope_emits_sd_scope_empty() -> None:
    binding = bind_synthesis_evidence_v1(envelope={}, retrieval_hits=[])
    assert any(r.get("sd_code") == SD_SCOPE_EMPTY_V1 for r in binding["synthesis_omission_rows"])


def test_citation_envelope_digest_stable() -> None:
    citations = build_synthesis_citations_from_hits_v1([_sample_hit()])
    a = build_synthesis_citation_envelope_v1(citations)
    b = build_synthesis_citation_envelope_v1(citations)
    assert a["citation_envelope_digest"] == b["citation_envelope_digest"]


def test_verify_gp08_cite01_static_gates_pass() -> None:
    for fn in (
        verify_gp08_cite01_citation_schema_static,
        verify_gp08_cite01_cite_or_omit_static,
        verify_gp08_cite01_envelope_digest_stable_static,
    ):
        out = fn()
        assert out["id"] == GP08_CITE01_GATE_ID_V1
        assert out["passed"] is True


def test_citation_law_catalog_references_syn_law_09() -> None:
    cat = build_synthesis_citation_law_catalog_v1()
    assert cat["syn_law_rule"] == SYN_LAW_09_RULE_ID_V1
    assert SD_CITE_GAP_V1 in cat["sd_codes"]


def test_doctrine_citations_section_present() -> None:
    root = _repo_root_containing_phase08_docs()
    text = (root / "DOCS" / "cortex" / "synthesis" / "phase-08-data-contracts.md").read_text(
        encoding="utf-8",
    )
    assert "SynthesisCitationV1" in text
    assert "claim_id" in text


def test_orchestrator_bind_populates_claim_slots(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = {
        "schema_version": 1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
        "pinned_retrieval_receipt": {"retrieval_response": _legal_retrieval_with_hit()},
    }
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    bind_row = next(row for row in out["execution_trace"] if row["phase"] == "BIND")
    assert bind_row["evidence_scope_summary"]["citation_count"] == 1
    assert len(out["claims"]) == 1
    assert out["synthesis_citation_envelope"]["citation_count"] == 1
    assert out["synthesis_job_receipt"]["claims"][0]["citations"] == ["cite-0000"]
