"""P08-08 — Synthesis replay identity + receipt law (``synthesis.synthesis_replay_equivalence``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.normative import (
    PHASE08_REPLAY_IDENTITY_FIELD_V1,
    PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import synthesis_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    GP08_REPLAY_01_GATE_ID_V1,
    PHASE08_SYNTHESIS_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION,
    SynthesisReplayEquivalenceError,
    build_synthesis_job_receipt_v1,
    build_synthesis_replay_equivalence_twin_diff_v1,
    build_synthesis_replay_explorer_catalog_v1,
    compare_gp08_replay_01_double_run_v1,
    compute_synthesis_job_replay_identity_v1,
    enforce_synthesis_expected_replay_identity_v1,
    hash_synthesis_job_replay_identity_v1,
    verify_gp08_replay01_canonical_identity_stable_static,
    verify_gp08_replay01_double_run_match_static,
    verify_gp08_replay01_receipt_embed_law_static,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _repo_root_containing_phase08_replay_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-replay-equivalence-spec.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/synthesis/ from test file parents.")


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8rep-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Rep User")
    tenant = Tenant(
        company_name="P8REP",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8rep-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _minimal_envelope(tenant_id: uuid.UUID) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
    }


def test_phase08_replay_equivalence_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION >= 1


def test_synthesis_replay_identity_is_deterministic_sha256() -> None:
    envelope = {
        "schema_version": 1,
        "tenant_id": "00000000-0000-0000-0000-000000000000",
        "synthesis_workload_class": "pipeline_default",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_pins": {"index_epoch": "epoch-1"},
        "_synthesis_policy_pack_digest": synthesis_policy_pack_digest_v1(),
    }
    subqueries = [{"retrieval_query_replay_identity": "a" * 64}]
    id_a = compute_synthesis_job_replay_identity_v1(
        envelope=envelope,
        retrieval_ingress_digest="b" * 64,
        retrieval_subqueries=subqueries,
    )
    id_b = compute_synthesis_job_replay_identity_v1(
        envelope=envelope,
        retrieval_ingress_digest="b" * 64,
        retrieval_subqueries=subqueries,
    )
    assert id_a == id_b
    assert len(id_a) == 64


def test_expected_replay_identity_pin_mismatch_raises() -> None:
    envelope = {
        "schema_version": 1,
        "synthesis_workload_class": "pipeline_default",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "expected_synthesis_job_replay_identity": "f" * 64,
    }
    with pytest.raises(SynthesisReplayEquivalenceError, match="expected_synthesis_job_replay_identity_mismatch"):
        enforce_synthesis_expected_replay_identity_v1(
            envelope,
            computed_identity="a" * 64,
        )


def test_gp08_replay_01_double_run_compare() -> None:
    identity = "d" * 64
    base = {
        PHASE08_REPLAY_IDENTITY_FIELD_V1: identity,
        "synthesis_job_receipt": {"receipt_digest": "e" * 64, "retrieval_subqueries": []},
    }
    compare_gp08_replay_01_double_run_v1(base, dict(base))


def test_twin_diff_detects_mismatch() -> None:
    a = {
        PHASE08_REPLAY_IDENTITY_FIELD_V1: "a" * 64,
        "synthesis_job_receipt": {"receipt_digest": "b" * 64, "retrieval_subqueries": []},
    }
    b = dict(a)
    b[PHASE08_REPLAY_IDENTITY_FIELD_V1] = "c" * 64
    diff = build_synthesis_replay_equivalence_twin_diff_v1(a, b)
    assert diff["gp08_replay_01_passed"] is False


def test_receipt_includes_upstream_replay_identity() -> None:
    receipt = build_synthesis_job_receipt_v1(
        tenant_id="00000000-0000-0000-0000-000000000001",
        job_id="00000000-0000-0000-0000-000000000002",
        envelope={
            "synthesis_workload_class": "pipeline_default",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
        },
        execution_trace=[{"phase": "RECEIPT"}],
        synthesis_legality_class="synthesis_replay_safe",
        synthesis_job_replay_identity="a" * 64,
        retrieval_ingress_digest="b" * 64,
        retrieval_subqueries=[{PHASE07_REPLAY_IDENTITY_FIELD_V1: "c" * 64}],
    )
    body = receipt["receipt_body"]
    assert body[PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1] == "c" * 64
    assert receipt.get("retrieval_receipt_embed", {}).get("retrieval_receipt_embed_digest")


def test_verify_gp08_replay_01_static_gates_pass() -> None:
    for fn in (
        verify_gp08_replay01_canonical_identity_stable_static,
        verify_gp08_replay01_double_run_match_static,
        verify_gp08_replay01_receipt_embed_law_static,
    ):
        out = fn()
        assert out["id"] == GP08_REPLAY_01_GATE_ID_V1
        assert out["passed"] is True


def test_forbidden_replay_key_rejected_on_hash() -> None:
    with pytest.raises(SynthesisReplayEquivalenceError, match="forbidden_replay_identity_key"):
        hash_synthesis_job_replay_identity_v1({"llm_completion_text": "nope"})


def test_doctrine_replay_spec_present() -> None:
    root = _repo_root_containing_phase08_replay_docs()
    text = (root / "DOCS" / "cortex" / "synthesis" / "phase-08-replay-equivalence-spec.md").read_text(
        encoding="utf-8",
    )
    assert PHASE08_REPLAY_IDENTITY_FIELD_V1 in text
    assert "G-P08-REPLAY-01" in text or "G‑P08‑REPLAY‑01" in text


def test_replay_explorer_catalog_shape() -> None:
    cat = build_synthesis_replay_explorer_catalog_v1(tenant_id="t1")
    assert cat["surface_kind"] == "synthesis_replay_explorer"
    assert cat["replay_identity_field"] == PHASE08_REPLAY_IDENTITY_FIELD_V1
    assert "synthesis_replay_divergence_total" in cat


def test_job_run_persists_replay_identity(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    out = execute_synthesis_job_envelope_v1(
        db_session,
        tenant_id=tenant_id,
        body=_minimal_envelope(tenant_id),
    )
    assert len(out["synthesis_job_replay_identity"]) == 64
    receipt = out["synthesis_job_receipt"]
    assert receipt["receipt_body"][PHASE08_REPLAY_IDENTITY_FIELD_V1] == out["synthesis_job_replay_identity"]
