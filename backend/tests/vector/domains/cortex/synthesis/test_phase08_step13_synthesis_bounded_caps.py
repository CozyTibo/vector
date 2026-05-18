"""Phase 08 Step 13 — bounded caps + SD-* registry."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_degradation import apply_synthesis_degradation_taxonomy_v1
from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
    GP08_DEG01_GATE_ID_V1,
    SD_CAP_CLAIMS_V1,
    SD_CITE_GAP_V1,
    SYNTHESIS_SD_CODES_REGISTRY_V1,
    SynthesisBoundedCapsError,
    apply_synthesis_policy_pack_caps_v1,
    assert_synthesis_artifact_under_byte_cap_v1,
    assert_synthesis_wall_budget_v1,
    build_synthesis_omission_explorer_catalog_v1,
    load_synthesis_policy_pack_v1,
    normalize_synthesis_omission_law_rows_v1,
    verify_gp08_deg01_sd_registry_closed_static,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8deg-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 DEG User")
    tenant = Tenant(
        company_name="P8DEG",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8deg-{uuid.uuid4().hex[:8]}",
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
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
    }


def _legal_retrieval_stub() -> dict[str, object]:
    return {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-deg",
        "retrieval_evidence_hits": [],
        "retrieval_omission_rows": [],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
    }


@pytest.mark.parametrize(
    "verifier",
    [verify_gp08_deg01_sd_registry_closed_static],
)
def test_gp08_deg01_static_gate(verifier: Callable[[], dict[str, Any]]) -> None:
    out = verifier()
    assert out["id"] == GP08_DEG01_GATE_ID_V1
    assert out["passed"] is True


def test_policy_pack_sd_codes_match_registry() -> None:
    pack = load_synthesis_policy_pack_v1()
    assert set(pack["sd_codes"]) == set(SYNTHESIS_SD_CODES_REGISTRY_V1)


def test_cap_ceiling_bypass_rejected() -> None:
    with pytest.raises(SynthesisBoundedCapsError, match="selection_policy_cap_ceiling_exceeded"):
        apply_synthesis_policy_pack_caps_v1("degradation_brief", {"max_claims": 10_000})


def test_omission_law_registry() -> None:
    rows = normalize_synthesis_omission_law_rows_v1([{"sd_code": SD_CITE_GAP_V1}])
    assert rows[0]["omission_semantics"] == "omitted_evidence"
    with pytest.raises(SynthesisBoundedCapsError, match="unknown_synthesis_omission_class"):
        normalize_synthesis_omission_law_rows_v1([{"sd_code": "SD-NOT-REAL"}])


def test_apply_degradation_taxonomy_includes_sd_multiset() -> None:
    tax = apply_synthesis_degradation_taxonomy_v1(
        synthesis_omission_rows=[{"sd_code": SD_CITE_GAP_V1}],
        synthesis_legality_class="synthesis_degraded",
    )
    assert SD_CITE_GAP_V1 in tax["sd_codes_sorted"]
    assert tax["synthesis_degradation_posture"] in {"degraded", "critical", "unresolved"}


def test_413_artifact_too_large() -> None:
    with pytest.raises(SynthesisBoundedCapsError) as exc:
        assert_synthesis_artifact_under_byte_cap_v1({"blob": "x" * 500}, max_artifact_json_bytes=20)
    assert exc.value.http_status == 413


def test_503_wall_timeout() -> None:
    with pytest.raises(SynthesisBoundedCapsError) as exc:
        assert_synthesis_wall_budget_v1(elapsed_ms=200_000, max_wall_ms=120_000)
    assert exc.value.http_status == 503


def test_omission_explorer_catalog() -> None:
    cat = build_synthesis_omission_explorer_catalog_v1()
    assert cat["gate_id"] == GP08_DEG01_GATE_ID_V1
    assert set(cat["sd_codes_registry"]) == set(SYNTHESIS_SD_CODES_REGISTRY_V1)


def test_orchestrator_receipt_has_degradation_rollup(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)
    body["pinned_retrieval_receipt"] = {"retrieval_response": _legal_retrieval_stub()}
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    receipt = out["synthesis_job_receipt"]
    assert receipt.get("synthesis_degradation_rollup")
    vector = receipt.get("synthesis_job_replay_identity_vector") or {}
    assert "sd_codes_sorted" in vector
    classify_row = next(row for row in out["execution_trace"] if row["phase"] == "CLASSIFY")
    assert classify_row.get("substrate_health_state")
